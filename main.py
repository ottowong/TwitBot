from tweetcapture import TweetCapture
import os
import re
import asyncio
import requests
import boto3
from datetime import datetime
import discord
from dotenv import load_dotenv

# Load environment values
load_dotenv()
api_endpoint = os.getenv("API_ENDPOINT")
discord_token = os.getenv("DISCORD_TOKEN")
media_url = os.getenv("MEDIA_URL").rstrip('/')

s3_region_name = os.getenv("S3_REGION_NAME")
s3_endpoint_url = os.getenv("S3_ENDPOINT_URL")
s3_aws_access_key_id = os.getenv("S3_AWS_ACCESS_KEY_ID")
s3_aws_secret_access_key = os.getenv("S3_AWS_SECRET_ACCESS_KEY")
s3_space = os.getenv("S3_SPACE")

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Create a discord client with intents
client = discord.Client(intents=intents)

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def download_video(url, filename):
    response = requests.get(url)

    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print("Video downloaded successfully.")
    else:
        print("Failed to download the video.")

@client.event
async def on_ready():
    print('Ready')

@client.event
async def on_message(message):
    content = message.content
    print("CONTENT: ", content)
    print()
    if ("https://twitter.com" in content) or ("https://x.com" in content) or ("http://twitter.com" in content) or ("http://x.com" in content):
        try:
            content = content.replace("https://x.com", "https://twitter.com")
            content = content.replace("http://x.com", "https://twitter.com")
            content = content.replace("http://twitter.com", "https://twitter.com")
        except Exception as e:
            print(e)

        url_pattern = r'https?://\S+'
        urls = re.findall(url_pattern, content)
        link = urls[0]
        print(link)

        username = link.split('/')[3]
        tweet_id = link.split('/')[5]
        video_filename = f"{username}_{tweet_id}.mp4"
        video_url = f"{media_url}/x/{video_filename}"

        response = requests.head(video_url)
        if response.status_code == 200:
            await message.reply(f"Repost!\n{video_url}")
            return
        
        videoFlag = False
        try:
            data = {
                "url": link
            }
            response = requests.post(api_endpoint, json=data, headers=headers)
            if response.status_code == 200:
                print("API ping successful!")
                print("Response:")
                video_url = response.json()["url"]
                print(video_url)
                if('video.' in video_url):
                    download_video(video_url, video_filename)
                else:
                    raise ValueError(f"'{video_url}' - not a video")
                with open(video_filename, 'rb') as f:
                    video = discord.File(f)
                    fileslist = [video]
                    videoFlag = True
                    await message.reply(files=fileslist)
                os.remove(video_filename)
                print("video deleted")
            else:
                raise Exception(f"Failed to ping API. Status code: {response.status_code}\n{response}")
        except Exception as e:
            if(videoFlag):
                
                Bsession = boto3.session.Session()
                Bclient = Bsession.client('s3',
                    region_name=s3_region_name,
                    endpoint_url=s3_endpoint_url,
                    aws_access_key_id=s3_aws_access_key_id,
                    aws_secret_access_key=s3_aws_secret_access_key
                )
                Bclient.upload_file(video_filename,
                s3_space,
                f'x/{video_filename}',
                ExtraArgs={'ACL':'public-read','ContentType':'video/mp4'})
                os.remove(video_filename)
                await message.reply(f'Video is too big for Discord\n{video_url}')
            else:
                try:
                    print(e)
                
                    tweet = TweetCapture(link)
                    filename = datetime.now().strftime("tweet-%Y%m%d%H%M%S%f")+".png"
                    print("taking screenshot...")
                    await tweet.screenshot(link, filename, mode=3, night_mode=1)
                    print("screenshot taken")
                    
                    with open(filename, 'rb') as f:
                        picture = discord.File(f)
                        fileslist = [picture]
                        await message.reply(files=[picture])
                    os.remove(filename)
                    print("image deleted")
                except Exception as e2:
                    print(e)
                    await message.reply("Error: " + str(e2) + "\n(" + str(e) + ")")

client.run(discord_token)
