import openai
import json
import os
import subprocess
import mysql.connector
from google.cloud import speech

# Load the configuration from the file
with open('NOUPLOAD/secretsConfig.json') as config_file:
    config = json.load(config_file)

# Extract the API key
api_key = config["openAIKey"]

# Initialize the OpenAI API client
openai.api_key = api_key

# Set the path to your Google Cloud service account key JSON file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'NOUPLOAD/price-tracker-53480-15525c6f9474.json'

# Initialize the Google Cloud Speech client
speech_client = speech.SpeechClient()

# Set your database connection parameters
db_config = {
    "host": config["planetScaleCredentials"]["host"],
    "user": config["planetScaleCredentials"]["user"],
    "password": config["planetScaleCredentials"]["password"],
    "database": config["planetScaleCredentials"]["database"],
}

# Inventory provided by the user
with open('inventory.json') as inventoryFile:
    inventory = json.load(inventoryFile)


def convert_order_description(order_description):
    formatted_inventory = ', '.join([f'{code} {name}' for name, code in inventory.items()])
    prompt = f"Convert the order description to the desired format (eg. 1 Cheese Taco, 2 Baja Blast) using the following inventory items (items should not be plural eg. 2 cheese tacos should be written as 2 cheese taco) If they add a modification, format the item like this (eg. 1 Cheese taco with beans): {formatted_inventory}\n\n{order_description}\n\nConverted order: "
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=50,
        stop=None,
        temperature=0,
    )
    if response.choices[0].text.strip()[:-1] == '.':
        return response.choices[0].text.strip()[:-1]
    else:
        return response.choices[0].text.strip()

def transcribe_m4a(audio_path):
    wav_path = audio_path.replace('.m4a', '.wav')
    subprocess.run(['ffmpeg', '-i', audio_path, '-acodec', 'pcm_s16le', '-ar', '16000', wav_path])
    
    with open(wav_path, 'rb') as audio_file:
        audio_content = audio_file.read()

    audio = speech.RecognitionAudio(content=audio_content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )

    response = speech_client.recognize(config=config, audio=audio)

    transcribed_text = ""
    for result in response.results:
        transcribed_text += result.alternatives[0].transcript + " "

    os.remove(wav_path)
    
    return transcribed_text.strip()

def generate_sql_queries(order_description):
    orders = order_description.split(', ')
    sql_queries = []

    for order in orders:
        parts = order.strip().split(' ')
        quantity = int(parts[0])
        item_name_parts = parts[1:]
        item_name = ' '.join(item_name_parts)
        modifications = None

        # Check if modifications are provided
        if 'with' in item_name_parts:
            modifications_index = item_name_parts.index('with')
            modifications = ' '.join(item_name_parts[modifications_index + 1:])
            item_name = ' '.join(item_name_parts[:modifications_index])

        if item_name in inventory:
            item_code = inventory[item_name]
            sql_queries.append(f"INSERT INTO outGoingOrders (itemName, modifications, quantity, price)\nVALUES ('{item_name}', '{modifications}', {quantity}, {item_code});")

    return sql_queries

def generate_and_execute_sql_queries(sql_queries):
    try:
        db_connection = mysql.connector.connect(**db_config)
        cursor = db_connection.cursor()

        for query in sql_queries:
            print("Executing query:", query)
            cursor.execute(query)
            db_connection.commit()

        print("All queries executed successfully!")

    except mysql.connector.Error as err:
        print("Error:", err)

    finally:
        cursor.close()
        db_connection.close()

def main():
    print("Welcome to the AI Order Processor!")
    print("Provide the inventory in the format 'Item Name: Item Code' (e.g., 'Cheesy Potatoes: 1')")

    print("\nInventory:")
    for item_name, item_code in inventory.items():
        print(f"{item_name}: {item_code}")
    
    audio_path = "order5.m4a"
    
    transcribed_text = transcribe_m4a(audio_path)
    print("\nTranscribed Text:")
    print(transcribed_text)
    
    converted_order = convert_order_description(transcribed_text)
    print("\nConverted Order Description:")
    print(converted_order)
    
    sql_queries = generate_sql_queries(converted_order)
    print("\nGenerated SQL Queries:\n")
    for query in sql_queries:
        print(query)

    generate_and_execute_sql_queries(sql_queries)

if __name__ == "__main__":
    main()
