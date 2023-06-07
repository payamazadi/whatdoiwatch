import csv
import pandas as pd
import base64
from io import StringIO
import json
from typing import Dict

def parse_upload():
     # Extract the file content from the event
    # event['body'] should contain the base64-encoded string
    file_content = base64.b64decode(event['body'])

    # Convert binary data to string format
    data = file_content.decode('utf-8')

    # Convert the CSV data to a pandas DataFrame
    df = pd.read_csv(StringIO(data))
    
    # Convert duration column to datetime format
    df['Duration'] = pd.to_timedelta(df['Duration'])

    # Filter out HOOK, TRAILER, etc
    df = df[df['Supplemental Video Type'].isna()]
    
    # Filter rows that have a duration less than 12 minutes
    df = df[df['Duration'] >= pd.Timedelta(minutes=12)]

    # Remove everything after the first colon in 'Title'
    df['Title'] = df['Title'].str.split(':').str[0]
    
    # Count rows per title and convert to dictionary
    return df['Title'].value_counts().to_dict()

def main(event, context) -> Dict[str, int]:

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,POST',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

   watched_dict = parse_upload()
    

    # Return the dictionary as a JSON response
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(watched_dict)
    }
