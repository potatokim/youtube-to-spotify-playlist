# -*- coding: utf-8 -*-
import json
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
from youtube_title_parse import get_artist_title
import spotify_token as spotify_token

from spotify_client_secret import sp_dc, sp_key, spotify_user_id

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

class Main:


    def __init__(self):
        data = spotify_token.start_session(sp_dc, sp_key)
        # expiration_date = data[1]
        
        self.spotify_user_id = spotify_user_id
        self.spotify_access_token = data[0]
        self.youtube_client = self.get_youtube_client()


    def get_youtube_client(self):
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "youtube_client_secret.json"
    
        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)
        
        return youtube_client
    

    def get_youtube_videos(self):  
        playlist_id = "SOME_YOUTUBE_PLAYLIST_ID"
        request = self.youtube_client.playlistItems().list(
                part="snippet,contentDetails",
                maxResults=25,
                playlistId=playlist_id
        )
        response = request.execute()

        return response["items"]


    def generate_track_info(self, youtube_videos):
        tracks = {}
        for video in youtube_videos:
            video_title = video["snippet"]["title"]
            video_url = "https://www.youtube.com/watch?v={}".format(video["id"])
            track_artist, track_title = get_artist_title(video_title)
            spotify_uri = self.get_spotify_URI(track_title, track_artist)
            
            if track_title is not None and track_artist is not None and spotify_uri != "":
                tracks[video_title] = {
                        "track": track_title,
                        "artist": track_artist,
                        "youtube_url": video_url,
                        "spotify_uri": spotify_uri
                }

        return tracks
            

    def get_spotify_URI(self, track_title, track_artist):
        query = "https://api.spotify.com/v1/search?q=track:{}%20artist:{}&type=track&limit=1".format(track_title, track_artist)
        response = requests.get(query,
                                headers={
                                        "Content-Type": "application/json",
                                        "Authorization": "Bearer {}".format(self.spotify_access_token)
                                        }
                                )
        response_json = response.json()
        tracks = response_json["tracks"]["items"]
        uri = tracks[0]["uri"] if len(tracks) > 0 else ""
        
        return uri


    def create_spotify_playlist(self):
        request_body = json.dumps(
            {
              "name": "From Youtube",
              "description": "Songs automatically saved from Youtube video.",
              "public": True
            }
        )
        query = "https://api.spotify.com/v1/users/{}/playlists".format(self.spotify_user_id)
        response = requests.post(query, 
                                 data=request_body, 
                                 headers={
                                         "Content-Type": "application/json",
                                         "Authorization": "Bearer {}".format(self.spotify_access_token)
                                         }
                                 )

        # .json is requests library's built-in JSON decoder; return Python dictionary's object
        response_json = response.json()

        return response_json["id"] # return playlist's ID
    

    def add_songs_to_spotify_playlist(self):
        youtube_videos = self.get_youtube_videos()
        tracks = self.generate_track_info(youtube_videos)
        spotify_playlist_id = self.create_spotify_playlist()

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(spotify_playlist_id)

        spotify_uris = []
        # track-info: Python's dictionary of key-value pair as tuples in a list
        for track, info in tracks.items():
            spotify_uris.append(info["spotify_uri"])

        spotify_uris_json = json.dumps(spotify_uris)

        response = requests.post(query,
                                data = spotify_uris_json,
                                headers={
                                        "Content-Type": "application/json",
                                        "Authorization": "Bearer {}".format(self.spotify_access_token)
                                        }
                                )
        
        # TODO: Check for valid response code

        response_json = response.json()
        
        return response_json
        
    
if __name__ == "__main__":
    app = Main()
    app.add_songs_to_spotify_playlist()
