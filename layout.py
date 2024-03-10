import chainlit as cl
from backend import healthily, login
import json
from fpdf import FPDF
from backend.utils import get_best_match
import requests


#Disctionary to define questions
initial_questions = {
    "name": "Please enter your Name.",
    "gender": "Please enter your Gender.",
    "yob": "Please enter your Year of Birth.",
    "symptoms": "Please help me with the symptoms you are experiencing today.",
    #"medical_history": "Explain your medical history (chronic diseases, smoking and drinking habits).",
}

# Dictionary to store user answers
user_answers = {
    "name": None,
    "gender": None,
    "yob": None,
    "symptoms": None,
} 

user_agreed = False

all_ids = []          # List to store all available IDs


async def next_question(response, api):
    global all_ids
    if response['question']['type'] in ["name","health_background","factor", "symptoms", "autocomplete","symptom"]:
        question = ' '.join([question['text'] for question in response['question']['messages']])
    else:
        question = ' '.join([question['value'] for question in response['question']['messages']])
    choices = {}

    if 'choices' in response['question']:
        choice_value = 'label'
        if response['question']['type'] == 'health_background':
            choice_value = 'long_name'
        elif response['question']['type'] in ["factor","symptoms", "autocomplete", "symptom"]:
            choice_value = 'text'
        choices = {choice['id']: choice[choice_value] for choice in response['question']['choices']}
        options = ', '.join(choices.values())
        all_ids = list(choices.keys())
        chosen_ids = [] 
        not_chosen_ids = []
        elements = [
            cl.Text(name=question, content=options, display="inline")
        ]
        await cl.Message(
            content="",
            elements=elements,
        ).send()
        if response["conversation"]["phase"] == "autocomplete_add":
            user_response = await  cl.AskUserMessage(content="",).send()
            user_input = user_response['output']
            choices = await api.search(user_input)
            options = ', '.join(choices.values())
            elements = [cl.Text(name="Please select which one is the most accurate", content=options, display="inline")]
            await cl.Message(
            content="",
            elements=elements,
            ).send()
        else:
            user_response = await  cl.AskUserMessage(content="Type what option(s) apply to you or enter No",).send()
        user_input = user_response['output']
        chosen_values = user_input.split(', ')

        for choice_value in chosen_values:
            chosen_value = get_best_match(choice_value,list(choices.values()))
            if chosen_value:
                for key,value in choices.items():
                    if value == chosen_value:
                        chosen_ids.append(key)
                        break
        
        for id in all_ids:
            if id not in chosen_ids:
                not_chosen_ids.append(id)

        print("All:", all_ids)
        print("Choosen:", chosen_ids)
        print("Not Choosen:", not_chosen_ids)
    else:
        user_response = await  cl.AskUserMessage(content=question,).send()
    answer_type = response['question']['type']

    response = await api.respond_to_healthily(chosen_ids, not_chosen_ids, answer_type)

    return response

async def parse_report(response):
    name = response['user']['name']
    gender = response['user']['gender']
    age = response['user']['age']
    #message = ' '.join([message['value'] for message in response['question']['messages']])
    diagnosis_possible = response['report']['summary']['diagnosis_possible']
    main_symptoms = [symptom['name'] for symptom in response['report']['summary']['extracted_symptoms']]
    duration = response['report']['summary']['duration']
    additional_symptoms = [symptom['name'] for symptom in response['report']['summary']['additional_symptoms']]
    unsure_symptoms = [symptom['name'] for symptom in response['report']['summary']['unsure_symptoms']]
    advice = response['report']['summary']['consultation_triage']['triage_advice']
    advice_level = response['report']['summary']['consultation_triage']['level']
    #articles = response['report']['summary']['articles_v3']['content']
    influencing_factors = []
    for inf_factor in response['report']['summary']['influencing_factors']:
        if inf_factor['value']['value'] == True:
            influencing_factors.append(inf_factor['long_name'])

    #show report
    content = "Please find your consultation report below: \n\n Name: " + name + "\n Gender: " + gender + "\n Age: " + str(age) + "\n\n Diagnosis Possible: " + str(diagnosis_possible) + "\n Main Symptoms: " + str(main_symptoms) + "\n Duration of Main Symptoms: " + duration + "\n\n Additional Symptoms: " + str(additional_symptoms) + "\n Unsure Symptoms: " + str(unsure_symptoms) + "\n\n Advice: " + advice + "\n Advice Level: " + advice_level + "\n Influencing Factors: " + str(influencing_factors)
    actions = [
        cl.Action(name="Download Report", value=content, label="Download", description="Download Report")
    ]
    
    await cl.Message(content=content, actions=actions).send()



async def conversation():
    # Iterate over questions
    for key, question in initial_questions.items():
        answer = await cl.AskUserMessage(content=question).send()
        user_answers[key] = answer['output'] if answer else None

    # Storing user answers in variables
    user_name =  user_answers["name"]
    user_gender = user_answers["gender"]
    user_yob = user_answers["yob"]
    user_symptoms = user_answers["symptoms"]
    #user_medical_history = user_answers["medical_history"]

    global user_details

    user_details = ','.join(user_name)
    user_details = ','.join(user_gender)
    user_details = ','.join(user_yob)
    user_details = ','.join(user_symptoms)

    # Do something with the stored user answers
    #print("User's Details:", user_name, user_gender, user_yob)
    #print("User's Symptoms:", user_symptoms)
    #print("User's Medical History:", user_medical_history)
    api = healthily.HealthilyApi()
    response = await api.start_conversation(user_name, user_gender, user_yob, user_symptoms)
    # Parse JSON data
    #data = json.loads(response)

    # Extract question and choices
    while 'report' not in response:
        new_reponse = await next_question(response, api)
        response = new_reponse

    #Generate report
    if 'report' in response:
        await parse_report(response)
       

@cl.action_callback("Download Report")
async def download_pdf(action):
    # Create an instance of the FPDF class
    pdf = FPDF()

    # Add a page
    pdf.add_page()

    # Set the font (you can choose other fonts as well)
    pdf.set_font("Arial", size=15)

    # Insert a cell with the title
    pdf.cell(200, 10, txt="Consultation Report", ln=1, align='C')

    pdf.set_font("Arial", size=12)
    # Insert a cell with the description
    pdf.multi_cell(200, 10, txt=action.value, align='L')

    # Save the PDF with the filename "report.pdf"
    pdf.output("report.pdf")

    # pdf_url = "/report.pdf"
    # response = requests.get(pdf_url)

    # with open("downloaded_report.pdf", "wb") as pdf_file:
    #     pdf_file.write(response.content)


@cl.action_callback("Initial Assessment")
async def on_action(action):
    global user_agreed
    user_agreed = True
    # Remove the action button from the chatbot user interface
    await action.remove()
    cl.Text(name="simple_text", content="You have agreed to the Terms and Conditions", display="inline")
    response = await conversation()  # Trigger the conversation after the user has agreed
    #print(response)
    return True


@cl.on_chat_start
async def main():
    await cl.Avatar(
        name="Zenith Care",
        url="public/favicon.png",
    ).send()
    await cl.Avatar(
        name="You",
        url="public/user_icon.png",
    ).send()
    actions = [
        cl.Action(name="Initial Assessment", value="Agree", label="Agree", description="Agree")
    ]
    content = "Welcome to Zenith Care. Please agree to the following terms to start using Zenith Care: \n 1. I'm over 18. \n 2. Zenith Care and Healthily can process my health data to help me manage my health with recommendations, information, and care options, as described in the Privacy Policy. \n"
    await cl.Message(content=content, actions=actions).send()
