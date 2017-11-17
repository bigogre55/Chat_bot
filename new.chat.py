from flask import Flask, request, render_template, session, redirect, url_for, escape
import datetime
import random
from textblob import TextBlob

app = Flask(__name__)

app.secret_key = '9ec32eef84e19d677476502b91cfa1d604f4717354782a5d1a0d28a16ce7909383b4c6d87fa71834d3e6246691b28d75cd915f6a717f58671b843d140c3bf6ed'

greeting_input = ('hello','hey','hi',"what's up",'greetings','aloha')
greeting_output = ("'sup bro",'hey','*nods*',"yo!",'hi','greetings friend')
ugly_response = (" feel the same way",
                 " need to work on that",
                 " need to find someone else to talk to",
                 " would really like that to work out")

master_is = "I am owned by Jake The Ogre"

def master(q):
    if str(q.lower()) == "who is your master?":
        return master_is

def greeting_check(s):
    for word in s.words:
        if word.lower() in greeting_input:
            return random.choice(greeting_output)

def output(o):
    return o.upper() + " - I made it uppercase"

def find_pronoun(sent):
    """Given a sentence, find a preferred pronoun to respond with. Returns None if no candidate
    pronoun is found in the input"""
    pronoun = None

    for word, part_of_speech in sent.pos_tags:
        # Disambiguate pronouns
        if part_of_speech == 'PRP' and word.lower() == 'you':
            pronoun = 'I'
        elif part_of_speech == 'PRP' and word == 'I':
            # If the user mentioned themselves, then they will definitely be the pronoun
            pronoun = 'You'
    return pronoun

@app.route('/chat_bot/logout')
def logout():
   # remove the username from the session if it is there
   session.pop('user', None)
   return redirect(url_for('get_login'))

@app.route('/chat_bot/get_login', methods = ['GET', 'POST'])
def get_login():
   if request.method == 'POST':
      session['user'] = request.form['user']
      session['chat_in'] = "<br>"
      return redirect(url_for('chat'))
   return '''
   <html><head>
   <title>Chat_Bot</title></head><body>
   <p>Enter a username</p>
   <form action = "" method = "post">
      <p><input type = text name = 'user' autofocus/></p>
      <p><input type = submit value = 'Login'/></p>
   </form>
   </body></html>
   '''

@app.route('/chat_bot', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        username = session['user']
#        session['chat_in'] = "<br>"
        return 'Logged in as ' + username + '<br>' + \
        "<b><a href = '/chat_bot/logout'>click here to log out</a></b>"
    return "You are not logged in <br><a href = '/chat_bot/get_login'></b>" + \
      "click here to log in</b></a>"

@app.route('/chat_bot/chat', methods=['GET','POST'])
def chat():
    if not 'user' in session:
        return "You are not logged in <br><a href = '/chat_bot/get_login'></b>" + \
        "click here to log in</b></a>"
    username = session['user']
    status = 'Hello, ' + username + '! <br>' + \
    "<b><a href = '/chat_bot/logout'>click here to log out</a></b>"
    if request.method == 'POST':
        chat_input = TextBlob(request.form['chat_input'])
        out_text = output(chat_input)
        session['chat_in'] = session['chat_in'] + "<br>" + str(request.form['chat_input'])
    else:
        out_text = "Hello, " + username + "! My name is Chatter. It is Nice to meet you!"
        chat_out = out_text
        session['chat_out'] = "<br>"

    if 'chat_input' in locals():
      chat_out = master(chat_input)
      if not chat_out:
          chat_out = greeting_check(chat_input)

    if not 'chat_out' in locals():
        chat_out = None

    if chat_out == None and 'chat_input' in locals():
      chat_focus = find_pronoun(chat_input)
      if chat_focus == "I" and chat_input.sentiment.polarity == 0:
          chat_out = chat_focus + random.choice(ugly_response)
      elif chat_focus == "You" and chat_input.sentiment.polarity == 0:
          chat_out = chat_focus + random.choice(ugly_response)
      elif chat_input.sentiment.polarity < 0:
          chat_out = "I am sorry to hear that. What can I do to help?  " #+ str(chat_input.sentiment.polarity)
      elif chat_input.sentiment.polarity > 0:
          chat_out = "i am so glad to hear that! What else can I help you with?  " #+ str(chat_input.sentiment.polarity)
      else:
          chat_out = "I dont know what to say"

    session['chat_out'] = session['chat_out'] + '<br>' + chat_out
    now = datetime.datetime.now()
    timeString = now.strftime("%Y-%m-%d %H:%M")
    templateData = {
    'user_status' : status,
    'chat_output' : session['chat_out'],
    'chat_input' : session['chat_in'],
    'time': timeString,
    }

    return render_template("input.html", **templateData)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5060)
