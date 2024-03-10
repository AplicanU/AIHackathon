import chainlit as cl
from backend import healthily, login
import json
from backend.utils import get_best_match


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
       

async def next_question(response, api):
    global all_ids
    if response['question']['type'] in ["name","health_background","factor", "symptoms", "autocomplete"]:
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
        user_response = await  cl.AskUserMessage(content="Select what option(s) apply to you.",).send()
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

'''for choice_id, choice_label in choices.items():
        action = cl.Action(name="Further_Actions", value=choice_id, label=choice_label, description=choice_label)
        actions.append(action)
    selected_action = await cl.AskActionMessage(content=question, actions=actions).send()
    #await cl.Message(content=question, actions=actions).send()
    await further_action(selected_action)'''


    
'''async def further_action(action):
    global chosen_ids, not_chosen_ids
    not_chosen_ids = all_ids.copy()
    # Get the selected ID from the action
    selected_id = action["value"]

    # Add the selected ID to the chosen_ids dictionary
    chosen_ids[selected_id] = all_ids[selected_id]

    # Remove the selected ID from the not_chosen_ids dictionary
    del not_chosen_ids[selected_id]

    print("All:", all_ids)
    print("Choosen:", chosen_ids)
    print("Not Choosen:", not_chosen_ids)

    actions = []
    for choice_id, choice_label in not_chosen_ids.items():
        action = cl.Action(name="Further_Actions", value=choice_id, label=choice_label, description=choice_label)
        actions.append(action)
    selected_action = await cl.AskActionMessage(content="Select more option or submit", actions=actions).send()
    
'''



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
    actions = [
        cl.Action(name="Initial Assessment", value="Agree", label="Agree", description="Agree")
    ]
    content = "Welcome to Zenith Care. Please agree to the following terms to start using Zenith Care: \n 1. I'm over 18. \n 2. Zenith Care and Healthily can process my health data to help me manage my health with recommendations, information, and care options, as described in the Privacy Policy. \n"
    await cl.Message(content=content, actions=actions).send()
