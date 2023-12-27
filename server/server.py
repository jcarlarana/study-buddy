from flask import Flask, request, jsonify, send_file
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

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load OpenAI API key from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

def transcribe_audio(audio_file_path):
    with open(audio_file_path, 'rb') as audio_file:
        transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcription.text

def meeting_minutes(transcription):
    abstract_summary = abstract_summary_extraction(transcription)
    key_points = key_points_extraction(transcription)
    action_items = action_item_extraction(transcription)
    sentiment = sentiment_analysis(transcription)
    return {
        'abstract_summary': abstract_summary,
        'key_points': key_points,
        'action_items': action_items,
        'sentiment': sentiment
    }

def abstract_summary_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a highly skilled AI trained in language comprehension and summarization. I would like you to read the following text and summarize it into a concise abstract paragraph. Aim to retain the most important points, providing a coherent and readable summary that could help a person understand the main points of the discussion without needing to read the entire text. Please avoid unnecessary details or tangential points."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content


def key_points_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a proficient AI with a specialty in distilling information into key points. Based on the following text, identify and list the main points that were discussed or brought up. These should be the most important ideas, findings, or topics that are crucial to the essence of the discussion. Your goal is to provide a list that someone could read to quickly understand what was talked about."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

def action_item_extraction(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are an AI expert in analyzing conversations and extracting action items. Please review the text and identify any tasks, assignments, or actions that were agreed upon or mentioned as needing to be done. These could be tasks assigned to specific individuals, or general actions that the group has decided to take. Please list these action items clearly and concisely."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

def sentiment_analysis(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "As an AI with expertise in language and emotion analysis, your task is to analyze the sentiment of the following text. Please consider the overall tone of the discussion, the emotion conveyed by the language used, and the context in which words and phrases are used. Indicate whether the sentiment is generally positive, negative, or neutral, and provide brief explanations for your analysis where possible."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

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

@app.route('/save-as-pdf', methods=['POST'])
def save_as_pdf_endpoint():
    try:
        minutes = request.get_json()
        filename = request.form.get('filename', 'output/meeting_minutes.pdf')

        if not minutes:
            return jsonify({'error': 'Minutes data is missing'}), 400

        save_as_pdf(minutes, filename)

        return send_file(filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error during save as PDF endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
        print('Request Payload:', transcription)  # Log the payload

        if not transcription:
            return jsonify({'error': 'Transcription is missing'}), 400
        
        minutes = meeting_minutes(transcription)

        return jsonify(minutes)
    except Exception as e:
        print(f"Error during meeting minutes endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/generate', methods=['POST'])
def generate_endpoint():
    try:
        audio_file = request.files['audio']
        transcription = transcribe_audio(audio_file)
        minutes = meeting_minutes(transcription)
        logger.info(f"Generated meeting minutes: {minutes}")
        save_as_pdf(minutes, 'output/lecture_notes.pdf')
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error during generate endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/output/<filename>')
def download_file(filename):
    return send_from_directory('output', filename)


if __name__ == '__main__':
    app.run(debug=True)
