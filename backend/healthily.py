import httpx
import asyncio
import json
import os
import hashlib
from datetime import datetime
# Assuming these endpoints are defined somewhere in your Python config
healthily_chat_endpoint = "https://portal.your.md/v4/chat"
search_endpoint = "https://portal.your.md/v4/search/symptoms"
healthily_api_token = os.getenv('HEALTHILY_API_TOKEN', 'jmK9KVKDXsJpyRsnrTe9r1aMEEfAGSsq.X1rf6MAlzM3S2ySVZwM82fbSCdLAo25P')
healthily_login_endpoint = "https://portal.your.md/v4/login"
healthily_api_key = os.getenv('HEALTHILY_API_KEY', 'bt2xkYywWw9RDaLJv2PaU5dWwawfhUXH1tBYMpUI')
access_token = 'None'

class HealthilyApi:
    def __init__(self):
        self.last_used_key = dict()
        self.conversation_id = None
        self.access_token = None
        self.conversation_id = None

    async def login_http_request(self,url, body=None, header={}, method="GET"):
        headers = {"x-api-key": healthily_api_key, "Content-Type": "application/json"}
        headers.update(header)

        async with httpx.AsyncClient() as client:
            if method == "POST":
                response = await client.post(url, content=json.dumps(body) if body else None, headers=headers)
            else:  # GET request
                response = await client.get(url, headers=headers)
            
            response.raise_for_status()  # Raises an exception for 4XX/5XX responses

            if response.status_code not in [204, 404]:
                return {
                    "status": response.status_code,
                    "hasError": response.status_code >= 400,
                    "body": response.json()
                }
            else:
                return {
                    "status": response.status_code,
                    "hasError": response.status_code >= 400,
                    "body": None
                }

    async def auth_request(self,url, body={}, header={}):
        try:
            return await self.login_http_request(url, body, header, "POST")
        except httpx.HTTPStatusError as error:
            print(f"HTTP REQUEST ERROR: {{'url': {url}, 'message': {error.response.text}}}")
            raise

    def create_hash(self,stringified):
        hash_object = hashlib.sha256()
        # Update the hash object with the bytes-like object (encode the string to bytes)
        hash_object.update(stringified.encode())

        # Get the hexadecimal digest of the hash
        return hash_object.hexdigest()


    async def get_access_token(self,hash_object):
        body = {"id": str(hash_object)}
        header = {"Authorization": healthily_api_token}
        response = await self.auth_request(healthily_login_endpoint, body, header)
        return response["body"].get("access_token")

    async def http_request(self,url, token, body=None, method="POST"):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            if method == "POST":
                response = await client.post(url, json=body, headers=headers)
            else:  # for GET
                response = await client.get(url, headers=headers)
            
            response.raise_for_status()  # Raises exception for 4XX or 5XX status codes
            return response.json()

    async def initial_query(self,token, query=None):
        try:
            body = await self.http_request(healthily_chat_endpoint, token, body=query or {}, method="POST")
            return body
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400 and query:
                print(f"Error initiating request with query parameters: {query.get('answer', {})}")
                # Retry with empty body if the initial request with query fails with status 400
                body = await self.http_request(healthily_chat_endpoint, token, body={}, method="POST")
                return body
            else:
                raise

    async def send_response_query(self,query, token):
        body = await self.http_request(healthily_chat_endpoint, token, body=query, method="POST")
        return body

    async def search(self,query):
        url = f"{search_endpoint}?text={query}"
        body = await self.http_request(url, self.access_token, method="GET")
        answers = body["autocomplete"]
        keys_values = {answer["id"]: answer["user_facing_name"] for answer in answers}
        return keys_values

    def generate_answer_object(self,chosen_ids,not_chosen_ids, answer_type, conversation_id):
        # Some questions have constraints on them as well
        response = {}
        response["answer"] = {}
        if answer_type == 'generic':
            response["answer"] = {
            "type": "generic",
            "input": {
            "include": chosen_ids,
            "exclude": not_chosen_ids
            }
            }
        elif answer_type in ["symptom","symptoms","health_background","factor","autocomplete"]:
            response["answer"] = {
                "type": answer_type,
                "selection": chosen_ids,
            }
        response["conversation"] = {
                "id": conversation_id
            }
        return response

    async def login(self,name, gender, year_of_birth,initial_symptom):
        stringified = name + gender + str(year_of_birth) + initial_symptom
        stringified_hash = self.create_hash(stringified)
        self.access_token = await self.get_access_token(stringified_hash)
        global access_token
        access_token = self.access_token

    async def start_conversation(self,name, gender, year_of_birth,initial_symptom):
        get_token = await self.login(name, gender, year_of_birth,initial_symptom)
        print(get_token)
        query = {"answer": {
                "type": "entry",
                "name": name,
                "gender": gender,
                "year_of_birth": year_of_birth,
                "initial_symptom": initial_symptom,
                "other": False
                }}
        response = await self.initial_query(self.access_token, query=query)
        self.conversation_id = response["conversation"]["id"]
        print(json.dumps(response,indent=4))
        return response
    
    async def respond_to_healthily(self,chosen_ids,not_chosen_ids, answer_type,):
        request = self.generate_answer_object(chosen_ids,not_chosen_ids,answer_type,self.conversation_id)
        print("########################")
        print(request)
        response = await self.send_response_query(request,access_token)
        print(json.dumps(response,indent=4))
        return response
    