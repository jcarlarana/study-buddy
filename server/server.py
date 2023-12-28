from flask import Flask, request, jsonify, send_file
from flask_caching import Cache
from flask_cors import CORS 
import os
import logging
from openai import OpenAI
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from werkzeug.utils import secure_filename
from flask import send_from_directory
import time

from backoff import on_exception, expo, constant

app = Flask(__name__)
CORS(app)

# Configure Flask-Caching
cache = Cache(app, config={"CACHE_TYPE": "simple"})
#cache.clear()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load OpenAI API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# Function to transcribe audio
@cache.memoize(timeout=3600)  
def transcribe_audio(audio_file_path):
    with open(audio_file_path, 'rb') as audio_file:
        transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcription.text

# Function to split text into chunks
def chunk_text(text, chunk_size):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# Function to generate a cohesive passage from multiple sections
@on_exception(expo, Exception, max_tries=10, factor=4, logger=logging)
def generate_cohesive_passage(sections):
    prompt = (
        "You are an AI language model trained to generate cohesive passages."
        "You always use the correct formatting such as paragraphs, code blocks, scientific notation, bullet list and numbered lists, etc."
        "Given the following sections, create a single coherent passage that "
        "captures the main points and information."
    )

    # Concatenate sections into the prompt
    for section_name, section_content in sections.items():
        prompt += f"\n\n{section_name}:\n{section_content}"

    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        max_tokens=400,  # Adjust max_tokens based on your desired response length
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": ""}  # Empty user message to trigger the system response
        ]
    )

    return response.choices[0].message.content

# Function to generate meeting minutes for a transcription chunk

# Function to extract abstract summary from a transcription
@on_exception(expo, Exception, max_tries=10, factor=4, logger=logging)
def abstract_summary_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a highly skilled AI trained in language comprehension and summarization. I would like you to read the following text and summarize it into a concise abstract paragraph. Aim to retain the most important points, providing a coherent and readable summary that could help a person understand the main points of the discussion without needing to read the entire text. Please avoid unnecessary details or tangential points."},
            {"role": "user", "content": transcription}
        ]
    )
    return response.choices[0].message.content

# Function to extract key points from a transcription
@on_exception(expo, Exception, max_tries=10, factor=4, logger=logging)
def key_points_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a proficient AI with a specialty in distilling information into key points. Based on the following text, identify and list the main points that were discussed or brought up. These should be the most important ideas, findings, or topics that are crucial to the essence of the discussion. Your goal is to provide a list that someone could read to quickly understand what was talked about."},
            {"role": "user", "content": transcription}
        ]
    )
    return response.choices[0].message.content

# Function to extract action items from a transcription
@on_exception(expo, Exception, max_tries=10, factor=4, logger=logging)
def action_item_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are an AI expert in analyzing conversations and extracting action items. Please review the text and identify any tasks, assignments, or actions that were agreed upon or mentioned as needing to be done. These could be tasks assigned to specific individuals, or general actions that the group has decided to take. Please list these action items clearly and concisely."},
            {"role": "user", "content": transcription}
        ]
    )
    return response.choices[0].message.content

# Function to perform sentiment analysis on a transcription
@on_exception(expo, Exception, max_tries=10, factor=4, logger=logging)
def sentiment_analysis(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {"role": "system", "content": "As an AI with expertise in language and emotion analysis, your task is to analyze the sentiment of the following text. Please consider the overall tone of the discussion, the emotion conveyed by the language used, and the context in which words and phrases are used. Indicate whether the sentiment is generally positive, negative, or neutral, and provide brief explanations for your analysis where possible."},
            {"role": "user", "content": transcription}
        ]
    )
    return response.choices[0].message.content

# Function to save meeting minutes as PDF
def save_as_pdf(minutes, filename):
    pdf_filename = filename

    # Use ReportLab to generate PDF
    pdf = SimpleDocTemplate(pdf_filename, pagesize=letter)

    # Set styles for headings and content
    styles = getSampleStyleSheet()
    heading_style = styles['Heading1']
    content_style = ParagraphStyle(
        'Content',
        parent=styles['BodyText'],
        spaceAfter=12,
    )

    # Create a list to hold the content for the PDF
    pdf_content = []

    for key, value in minutes.items():
        heading = ' '.join(word.capitalize() for word in key.split('_'))

        # Add heading
        pdf_content.append(Paragraph(heading, heading_style))

        # Add content with text wrapping
        content_paragraphs = value.split('\n')
        for paragraph in content_paragraphs:
            pdf_content.append(Paragraph(paragraph, content_style))

        # Add space between sections
        pdf_content.append(Spacer(1, 12))

    # Build the PDF document
    pdf.build(pdf_content)

# Endpoint to save meeting minutes as PDF
@app.route('/save-as-pdf', methods=['POST'])
def save_as_pdf_endpoint():
    try:
        data = request.get_json()
        filename = data.get('filename', 'output/meeting_minutes.pdf')
        minutes = data.get('minutes')

        if not minutes:
            return jsonify({'error': 'Minutes data is missing'}), 400

        save_as_pdf(minutes, filename)

        return jsonify({'pdfUrl': f'/output/{filename}'}), 200
    except Exception as e:
        logger.error(f"Error during save as PDF endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Endpoint to transcribe audio
@app.route('/transcribe', methods=['POST'])
def transcribe_endpoint():
    try:
        # Assuming React application sends the audio file as a form-data POST request
        audio_file = request.files['audio']

        # Save the uploaded file to a temporary location
        filename = secure_filename(audio_file.filename)
        audio_file_path = os.path.join("temp_audio", filename)
        audio_file.save(audio_file_path)

        # Call the transcribe_audio function with the file path
        transcription = transcribe_audio(audio_file_path)

        # Optionally, you can remove the temporary file after transcription
        os.remove(audio_file_path)

        if transcription:
            return jsonify({'transcription': transcription})
        else:
            return jsonify({'error': 'Audio transcription failed'}), 500
    except Exception as e:
        logger.error(f"Error during transcription endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/meeting-minutes', methods=['POST'])
def meeting_minutes_endpoint():
    try:
        transcription = request.form.get('transcription')
        chunk_size = int(request.form.get('chunk_size', 25000))  # Default chunk size is 20000 characters

        if not transcription:
            return jsonify({'error': 'Transcription is missing'}), 400

        # Split the transcription into chunks
        transcription_chunks = chunk_text(transcription, chunk_size)

        # Initialize lists to store results for each category
        abstract_summary_list = []
        key_points_list = []
        action_items_list = []
        sentiment_list = []

        # Process each chunk separately
        for i, chunk in enumerate(transcription_chunks):
           # Introduce a 5-second delay between chunks
            if i > 0:
                time.sleep(1)

            # Extract information directly in the loop
            abstract_summary = abstract_summary_extraction(chunk)
            key_points = key_points_extraction(chunk)
            action_items = action_item_extraction(chunk)
            sentiment = sentiment_analysis(chunk)

            # Append the chunks into a list for each category
            abstract_summary_list.append(abstract_summary)
            key_points_list.append(key_points)
            action_items_list.append(action_items)
            sentiment_list.append(sentiment)

        # Join the lists into single strings for each category
        cohesive_abstract_summary = generate_cohesive_passage({'Abstract Summary': '\n'.join(abstract_summary_list)})
        cohesive_key_points = generate_cohesive_passage({'Key Points': '\n'.join(key_points_list)})
        cohesive_action_items = generate_cohesive_passage({'Action Items': '\n'.join(action_items_list)})
        cohesive_sentiment = generate_cohesive_passage({'Sentiment Analysis': '\n'.join(sentiment_list)})

        # Return only the cohesive passages
        final_results = {
            'Abstract Summary': cohesive_abstract_summary.strip(),
            'Key Points': cohesive_key_points.strip(),
            'Action Items': cohesive_action_items.strip(),
            'Sentiment Analysis': cohesive_sentiment.strip(),
        }

        logger.info(f"Generated meeting minutes: {final_results}")
        save_as_pdf(final_results, 'output/lecture_notes.pdf')
        return jsonify(final_results)

    except Exception as e:
        logger.error(f"Error during meeting minutes endpoint: {str(e)}")
        
        # Print the traceback to the console for debugging
        import traceback
        traceback.print_exc()

        return jsonify({'error': 'Internal server error'}), 500

# Endpoint to download generated PDF
@app.route('/output/<filename>')
def download_file(filename):
    return send_from_directory('output', filename)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)

