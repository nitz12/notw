from flask import Flask, redirect, request, session, url_for, render_template, send_file
import requests
import os
import random
from PIL import Image, ImageDraw
from io import BytesIO

app = Flask(__name__, template_folder='templates', static_folder='static')

app.secret_key = os.urandom(24)

# Replace these with your own LinkedIn API client ID and secret
CLIENT_ID = "861hitv0p8yt8e"
CLIENT_SECRET = "xZJWNRwEm20dhtcc"

# This is the URL that LinkedIn will redirect the user to after they authorize your app
REDIRECT_URI = "http://localhost:5000/callback"
REDIRECT_URI = "https://notw.nitz12.repl.co/callback"


@app.route("/")
def index():
  # Check if the user is already logged in
  if "access_token" in session:
    # If the user is logged in, redirect them to the profile page
    return redirect(url_for("profile"))
  else:
    # If the user is not logged in, redirect them to the LinkedIn login page
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=abc123&scope=r_emailaddress%20r_liteprofile"
    return render_template("home.html", auth_url=auth_url)
    #return redirect(auth_url)


@app.route("/callback")
def callback():
  # Get the authorization code from the query string
  code = request.args.get("code")

  # Exchange the authorization code for an access token
  token_url = "https://www.linkedin.com/oauth/v2/accessToken"
  data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
  }
  headers = {"Content-Type": "application/x-www-form-urlencoded"}
  response = requests.post(token_url, data=data, headers=headers)
  token_data = response.json()

  # Save the access token in the session
  session["access_token"] = token_data["access_token"]

  # Redirect the user to the profile page
  return redirect(url_for("profile"))


@app.route("/withFrame")
def withFrame():

  return render_template("profile_withframe.html",
                         name=session.get("first_name") + " " +
                         session.get("last_name"))


@app.route("/dlimg")
def dlimg():
  img_bytes = process_img()

  return send_file(img_bytes,
                   as_attachment=True,
                   download_name="img_with_frame.png",
                   mimetype='image/png')


def process_img():

  # Open the image
  im = Image.open(BytesIO(requests.get(session.get("prof_pic")).content))

  # default resizing
  print(im.size)
  im = im.resize((800, 800))

  # notw
  basedir = os.path.abspath(os.path.dirname(__file__))
  staticdir = os.path.join(basedir, 'static')
  notw_file_path = os.path.join(staticdir, "notw.png")

  notw = Image.open(notw_file_path)
  im.paste(notw, (0, 0), notw.convert('RGBA'))

  # Mask
  mask = Image.new('L', im.size, 0)
  draw = ImageDraw.Draw(mask)
  draw.ellipse((0, 0, im.width, im.height), fill=255)

  # Apply the mask to the image
  cropped_im = im.copy()
  cropped_im.putalpha(mask)

  image_io = BytesIO()
  cropped_im.save(image_io, format='PNG')
  image_io.seek(0)

  return (image_io)


@app.route("/getimg")
def getimg():

  img_bytes = process_img()

  return send_file(
    img_bytes,
    as_attachment=False,
    # download_name="cropped_img.png",
    mimetype='image/png')


@app.route("/profile")
def profile():
  # Check if the user is logged in
  if "access_token" not in session:
    # If the user is not logged in, redirect them to the login page
    return redirect(url_for("index"))

  # Get the user's profile information
  headers = {
    "Authorization": f"Bearer {session['access_token']}",
    "X-RestLi-Protocol-Version": "2.0.0"
  }
  response = requests.get("https://api.linkedin.com/v2/me", headers=headers)
  profile_data = response.json()

  # print("Profile Data")
  # print(profile_data.keys())
  firstname_local = profile_data['localizedFirstName']
  session["first_name"] = firstname_local

  lastname_local = profile_data['localizedLastName']
  session["last_name"] = lastname_local

  profile_id = profile_data['id']

  # Get the user's profile picture information
  profpic_resp = requests.get(
    "https://api.linkedin.com/v2/me?projection=(profilePicture(displayImage~digitalmediaAsset:playableStreams))",
    headers=headers)
  profpic_data = profpic_resp.json()

  ## 4 elements are returned with picture information four different scaling: 100*100, 200*200, 400*400 ,800*800
  max_size = 0
  max_size_link = ""

  for ele in profpic_data['profilePicture']['displayImage~']['elements']:

    width = ele['data'][list(ele['data'].keys())[0]]['displaySize']['width']
    height = ele['data'][list(ele['data'].keys())[0]]['displaySize']['height']
    size = width * height

    if size > max_size:
      max_size = size
      max_size_link = ele['identifiers'][0]['identifier']

  session['prof_pic'] = max_size_link

  #Get user's e-mail id
  mail_resp = requests.get(
    "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
    headers=headers)
  mail_id = mail_resp.json()['elements'][0]['handle~']['emailAddress']
  print(mail_id)

  # Render the profile page
  return render_template("profile.html",
                         name=session.get("first_name") + " " +
                         session.get("last_name"),
                         profile_picture_url=max_size_link)


if __name__ == "__main__":  # Makes sure this is the main process
  app.run(  # Starts the site
    host='0.0.0.0',  # EStablishes the host, required for repl to detect the site
    port=random.randint(2000,
                        9000)  # Randomly select the port the machine hosts on.
  )
