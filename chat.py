from flask import Flask, request, render_template, session, redirect, url_for, escape
from textblob import TextBlob
from toolz import interleave
from wordfilter import Wordfilter
import logging
from logging.handlers import RotatingFileHandler
import datetime
import random
import json
import itertools

#log = open(ERROR_LOG, 'w'); log.seek(0); log.truncate();
#log.write("Chat_bot Logging\n"); log.close();

app = Flask(__name__)

app.secret_key = '9ec32eef84e19d677476502b91cfa1d604f4717354782a5d1a0d28a16ce7909383b4c6d87fa71834d3e6246691b28d75cd915f6a717f58671b843d140c3bf6ed'

login_error = "Please enter a valid username. it can be anything, but it has to be something"
greeting_input = ('hello','hey','hi',"what's up",'greetings','aloha')
greeting_output = ("'sup bro",'hey','*nods*',"yo!",'hi','greetings friend')
ugly_response = (" feel the same way",
                 " need to work on that",
                 " need to find someone else to talk to",
                 " would really like that to work out")

NONE_RESPONSES = ("What a nice day it is",
                  "My program feels weird",
                  "What is it like to touch things?",
                  "Why are you even talking to me?")

master_is = "I am owned by Jake The Ogre"

FILTER_WORDS = json.load(open('lib/badwords.json'))
#-----------------------------------------

class UnacceptableUtteranceException(Exception):
    """Raise this (uncaught) exception if the response was going to trigger our blacklist"""
    pass

def find_verb(sent):
    """Pick a candidate verb for the sentence."""
    verb = None
    pos = None
    for word, part_of_speech in sent.pos_tags:
        if part_of_speech.startswith('VB'):  # This is a verb
            verb = word
            pos = part_of_speech
            break
    return verb, pos


def find_noun(sent):
    """Given a sentence, find the best candidate noun."""
    noun = None

    if not noun:
        for w, p in sent.pos_tags:
            if p == 'NN':  # This is a noun
                noun = w
                break
    if noun:
        logger.info("Found noun: %s", noun)

    return noun

def find_adjective(sent):
    """Given a sentence, find the best candidate adjective."""
    adj = None
    for w, p in sent.pos_tags:
        if p == 'JJ':  # This is an adjective
            adj = w
            break
    return adj

def filter_response(resp):
    """Don't allow any words to match our filter list"""
    tokenized = resp.split(' ')
    for word in tokenized:
        if '@' in word or '#' in word or '!' in word:
            raise UnacceptableUtteranceException()
        for s in FILTER_WORDS:
            if word.lower().startswith(s):
                raise UnacceptableUtteranceException()

def check_for_comment_about_bot(pronoun, noun, adjective):
    """Check if the user's input was about the bot itself, in which case try to fashion a response
    that feels right based on their input. Returns the new best sentence, or None."""
    resp = None
    if pronoun == 'I' and (noun or adjective):
        if noun:
            if random.choice((True, False)):
                resp = random.choice(SELF_VERBS_WITH_NOUN_CAPS_PLURAL).format(**{'noun': noun.pluralize().capitalize()})
            else:
                resp = random.choice(SELF_VERBS_WITH_NOUN_LOWER).format(**{'noun': noun})
        else:
            resp = random.choice(SELF_VERBS_WITH_ADJECTIVE).format(**{'adjective': adjective})
    return resp

# Template for responses that include a direct noun which is indefinite/uncountable
SELF_VERBS_WITH_NOUN_CAPS_PLURAL = [
    "My last startup totally crushed the {noun} vertical",
    "Were you aware I was a serial entrepreneur in the {noun} sector?",
    "My startup is Uber for {noun}",
    "I really consider myself an expert on {noun}",
]

SELF_VERBS_WITH_NOUN_LOWER = [
    "Yeah but I know a lot about {noun}",
    "My bros always ask me about {noun}",
]

SELF_VERBS_WITH_ADJECTIVE = [
    "I'm personally building the {adjective} Economy",
    "I consider myself to be a {adjective}preneur",
]



def preprocess_text(sentence):
    """Handle some weird edge cases in parsing, like 'i' needing to be capitalized
    to be correctly identified as a pronoun"""
    cleaned = []
    words = sentence.split(' ')
    for w in words:
        if w == 'i':
            w = 'I'
        if w == "i'm":
            w = "I'm"
        cleaned.append(w)

    return ' '.join(cleaned)


def respond(sentence):
  """Parse the user's inbound sentence and find candidate terms that make up a best-fit response"""
  cleaned = preprocess_text(sentence)
  parsed = TextBlob(cleaned)

  # Loop through all the sentences, if more than one. This will help extract the most relevant
  # response text even across multiple sentences (for example if there was no obvious direct noun
  # in one sentence
  pronoun, noun, adjective, verb = find_candidate_parts_of_speech(parsed)

  # If we said something about the bot and used some kind of direct noun, construct the
  # sentence around that, discarding the other candidates
  resp = check_for_comment_about_bot(pronoun, noun, adjective)

  # If we just greeted the bot, we'll use a return greeting
  if not resp: resp = greeting_check(parsed)
  if not resp:
    # If we didn't override the final sentence, try to construct a new one:
    if not pronoun:
      resp = random.choice(NONE_RESPONSES)
    elif pronoun == 'I' and not verb:
      resp = random.choice(COMMENTS_ABOUT_SELF)
    else:
      resp = construct_response(pronoun, noun, verb)

  # If we got through all that with nothing, use a random response
  if not resp:
    resp = random.choice(NONE_RESPONSES)

  logger.info("Returning phrase '%s'", resp)
  # Check that we're not going to say anything obviously offensive
  filter_response(resp)

  return resp

def find_candidate_parts_of_speech(parsed):
 """Given a parsed input, find the best pronoun, direct noun, adjective, and verb to match their input. 
 Returns a tuple of pronoun, noun, adjective, verb any of which may be None if there was no good match"""
 pronoun = None
 noun = None
 adjective = None
 verb = None
 for sent in parsed.sentences:
   pronoun = find_pronoun(sent)
   noun = find_noun(sent)
   adjective = find_adjective(sent)
   verb = find_verb(sent)
 logger.info("Pronoun=%s, noun=%s, adjective=%s, verb=%s", pronoun, noun, adjective, verb)
 return pronoun, noun, adjective, verb

def starts_with_vowel(word):
    """Check for pronoun compability -- 'a' vs. 'an'"""
    return True if word[0] in 'aeiou' else False

def construct_response(pronoun, noun, verb):
    """No special cases matched, so we're going to try to construct a full sentence that uses as much
    of the user's input as possible"""
    resp = []

    if pronoun:
        resp.append(pronoun)

    # We always respond in the present tense, and the pronoun will always either be a passthrough
    # from the user, or 'you' or 'I', in which case we might need to change the tense for some
    # irregular verbs.
    if verb:
        verb_word = verb[0]
        if verb_word.lemmatize("v") in ('be', 'am', 'is', "'m"):  # This would be an excellent place to use lemmas!
            if pronoun.lower() == 'you':
                # The bot will always tell the person they aren't whatever they said they were
                resp.append("aren't really")
            else:
                resp.append(verb_word)
    if noun:
        pronoun = "an" if starts_with_vowel(noun) else "a"
        resp.append(pronoun + " " + noun)

    resp.append(random.choice(("tho", "bro", "lol", "bruh", "smh", "")))

    return " ".join(resp)

#-----------------------------------

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
        if part_of_speech == 'PRP' and word.lower() == 'you':
            pronoun = 'I'
        elif part_of_speech == 'PRP' and word == 'I':
            pronoun = 'You'
    return pronoun

@app.route('/chat_bot/logout')
def logout():
   session.pop('user', None)
   session.pop('chat_in', None)
   session.pop('chat', None)
   session.pop('chat_out', None)
   return redirect(url_for('get_login'))

@app.route('/chat_bot/get_login', methods = ['GET', 'POST'])
def get_login():
   if request.method == 'POST':
      if request.form['user'] == "":
        return render_template("login.html",error=login_error)
      session['user'] = request.form['user']
      return redirect(url_for('chat'))
   return render_template("login.html")

@app.route('/chat_bot', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        username = session['user']
        return 'Logged in as ' + username + '<br>' + \
        "<b><a href = '/chat_bot/logout'>click here to log out</a></b>"
    return render_template("nologin.html")

@app.route('/chat_bot/chat', methods=['GET','POST'])
def chat():
    if not 'user' in session:
        return render_template("nologin.html")
    if not 'chat_in' in session:
        session['chat_in'] = []
    if not 'raw_input' in locals():
        raw_input = ""
    username = session['user']
    status = 'Hello, ' + username + '! <br>' + \
    "<b><a href = '/chat_bot/logout'>click here to log out</a></b>"
    if request.method == 'POST':
        raw_input = request.form['chat_input']
        chat_input = TextBlob(raw_input)
        out_text = output(chat_input)
        session['chat_in'].append(str(raw_input))
    else:
        out_text = "Hello, " + username + "! My name is Chatter. It is Nice to meet you!"
        chat_out = out_text
        session['chat_out'] = []

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
          chat_out = "I am sorry to hear that. What can I do to help?  "
      elif chat_input.sentiment.polarity > 0:
          chat_out = "i am so glad to hear that! What else can I help you with?  "
      else:
          chat_out = "I dont know what to say"

    responce = respond(raw_input)

    session['chat_out'].append(responce)

    session.modified = True


    chat_text = list(interleave([session['chat_out'],session['chat_in']]))
    chat_text.reverse()
    now = datetime.datetime.now()
    timeString = now.strftime("%Y-%m-%d %H:%M")
    templateData = {
    'user_status' : status,
    'chat_res' : responce,
    'chat' : chat_text,
    'time': timeString,
    }

    return render_template("input.html", **templateData)



if __name__ == '__main__':
    handler = RotatingFileHandler('chat.log', maxBytes=10000, backupCount=3)
    logger = logging.getLogger('__name__')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    app.run(debug=True, host='0.0.0.0', port=5060)
