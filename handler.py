import pandas as pd
import base64
from io import StringIO
import json
from typing import Dict
import urllib.parse
import requests

API_KEY = 'a6898ee32081c590e9d02cf377dee239'

def parse_upload(body):
     # Extract the file content from the event
    # event['body'] should contain the base64-encoded string
    file_content = base64.b64decode(body)

    # Convert binary data to string format
    data = file_content.decode('utf-8')

    # Convert the CSV data to a pandas DataFrame
    df = pd.read_csv(StringIO(data))

    # Remove the "US" identifier from the Netflix naming
    df['Title'] = df['Title'].str.replace(' (U.S.)', '')
    
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

def fetch_tv_show_ids(encoded_tv_shows):
    url_template = 'https://api.themoviedb.org/3/search/tv?api_key={API_KEY}&language=en-US&page=1&query={TV_SHOW_ENCODED}&include_adult=false'
    tv_show_ids = {}

    for show, count, encoded_show in encoded_tv_shows:
        url = url_template.format(API_KEY=API_KEY, TV_SHOW_ENCODED=encoded_show)
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200 and data.get('total_results', 0) > 0:
            tv_show_ids[show] = (count, data['results'][0]['id'])
        else:
            tv_show_ids[show] = (count, -1)
        print(f"Debug: {url}")

    return tv_show_ids


def get_tv_show_details(tv_show_ids):
    url_template = 'https://api.themoviedb.org/3/tv/{TV_SHOW_ID}?api_key={API_KEY}&language=en-US'
    tv_show_details = {}

    for show, (count, tv_show_id) in tv_show_ids.items():
        if tv_show_id == -1:
            tv_show_details[show] = (count, tv_show_id, -1, -1, "")
            continue

        url = url_template.format(TV_SHOW_ID=tv_show_id, API_KEY=API_KEY)
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            if data['episode_run_time']:
                episode_run_time = data['episode_run_time'][0]
            else:
                episode_run_time = 20
                print(f"Debug: {show} - No runtime data available, using default value.")

            number_of_episodes = data['number_of_episodes']
            if number_of_episodes == 0:
                number_of_episodes = 1
                print(f"Debug: {show} - Number of episodes reported as 0, using default value of 1.")

            tv_show_details[show] = (count, tv_show_id, number_of_episodes, episode_run_time, "TV")

    return tv_show_details

def clean_tv_show_details(tv_show_details):
    search_url_template = "https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&language=en-US&query={THE_SHOW}&page=1&include_adult=false"
    movie_url_template = "https://api.themoviedb.org/3/movie/{ID}?api_key={API_KEY}&language=en-US"

    cleaned_tv_show_details = tv_show_details.copy()

    for show, (count, tv_show_id, number_of_episodes, episode_run_time, item_type) in tv_show_details.items():
        if tv_show_id == -1:
            print(f"Debug: -------------------HERE WITH {show}")
            search_url = search_url_template.format(API_KEY=API_KEY, THE_SHOW=urllib.parse.quote(show))
            search_response = requests.get(search_url)
            search_data = search_response.json()

            if search_response.status_code == 200 and search_data["total_results"] > 0:
                movie_id = search_data["results"][0]["id"]
                movie_url = movie_url_template.format(ID=movie_id, API_KEY=API_KEY)
                movie_response = requests.get(movie_url)
                movie_data = movie_response.json()

                if movie_response.status_code == 200:
                    new_runtime = movie_data["runtime"]
                    cleaned_tv_show_details[show] = (count, movie_id, 1, new_runtime, "Movie")

    return cleaned_tv_show_details

def format_time(minutes, workday_hours=8):
        if minutes == -1:
            return 0
        
        work_minutes_in_day = workday_hours * 60
        workdays, remainder = divmod(minutes, work_minutes_in_day)
        hours, minutes = divmod(remainder, 60)
        return f"{workdays} workdays, {hours} hours, {minutes} minutes"

def summarize(tv_show_details):
     
    #csv_writer.writerow(["Name", "Type", "Times Watched", "Number of Eps", "Runtime", "Ratio", "Watched Time Pretty", "Watched Time"])
    for show, (count, tv_show_id, number_of_episodes, episode_run_time, item_type) in tv_show_details.items():
        print(f"Debug: Show: {show}, Count: {count}, Runtime: {episode_run_time}, NumEps: {number_of_episodes}")
        if tv_show_id == -1:
            ratio = -1
            total_time = "0"
            total_time_pretty = "0 workdays, 0 hours, 0 minutes"
        else:
            ratio = int(count) / number_of_episodes
            total_time_pretty = format_time(int(count) * episode_run_time)
            total_time = int(count) * episode_run_time

        tv_show_details[show] = (item_type, count, number_of_episodes, episode_run_time, ratio, total_time_pretty, total_time)
    #return {show: list(values) for show, values in tv_show_details.items()}
    summarized = [
        {
            "name": show,
            "type": values[0],
            "times_watched": values[1],
            "number_of_episodes": values[2],
            "episode_runtime": values[3],
            "ratio": values[4],
            "total_time_pretty": values[5],
            "total_time": values[6]
        }
        for show, values in tv_show_details.items()
    ]

    return summarized

        

def lambda_handler(event, context) -> Dict[str, int]:

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS,POST',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    watched_dict = parse_upload(event['body'])
    encoded_tv_shows = [(show, int(count), urllib.parse.quote(show)) for show, count in watched_dict.items()]
    tv_show_ids = fetch_tv_show_ids(encoded_tv_shows)
    tv_show_details = get_tv_show_details(tv_show_ids)
    cleaned_tv_show_details = clean_tv_show_details(tv_show_details)
    summarized = summarize(cleaned_tv_show_details)


    # Return the dictionary as a JSON response
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(summarized)
    }

if __name__ == "__main__":
    import sys
    #import json
    event_json = sys.argv[1] if len(sys.argv) > 1 else "{}"
    event_data = json.loads(event_json)
    
    result = lambda_handler(event_data, None)
    print(json.dumps(result, indent=4))
