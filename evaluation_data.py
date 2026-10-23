import os
from dotenv import load_dotenv
from random import randint, sample
from pandas import DataFrame
import json
import sys

#class import
from data_fetch import Data_fetch
from neo4j_manager import Neo4j_manager

load_dotenv()

#Receive person's identifier(s) and daily data
fetcher = Data_fetch()

with open("src\\personas.json") as file:
    json_data = json.load(file)

prompt_data = DataFrame(columns=["User", "System_prompt", "Prompt_body", "Full_prompt"])

def assign_intensity(MET_value):
    if MET_value < met_mpa_lower:
        return "light"
    elif met_mpa_lower <= MET_value <= met_mpa_higher:
        return "moderate"
    elif met_mpa_higher < MET_value <= met_vpa_higher:
        return "vigorous"
    else:
        return f"{MET_value} METs"

#Connect to neo4j database
neo4j = Neo4j_manager(
    uri = os.getenv('CLOUD_NEO4J_URI'),
    user = os.getenv('CLOUD_NEO4J_USERNAME'),
    password = os.getenv('CLOUD_NEO4J_PASSWORD')
    )

neo4j.connect()
connected = neo4j.neo4j_check_connection()
if connected == False:
    sys.exit("Failed to connect to Neo4j.")


DATABASE = os.getenv('CLOUD_NEO4J_DATABASE')


#####Loop through json personas
for person in json_data: 
    user_profile = person['profile']

    if user_profile == "CG":
        mpa_goal = 15
    else:
        mpa_goal = 30

    message_length = 80
    if user_profile == "SM":
        message_length = 50

   
    user_name = person['name']
    user_alias = person['name_alias']

    user_activity = fetcher.fetch_example_user(user_profile)

    ### Get weather
    current_temp, precipitation, precipitation_forecast = fetcher.fetch_weather_by_zipcode("enter zipcode")
    temp_forecast = f"Temperature: {current_temp}°C"
    location_restriction = fetcher.get_workout_location(current_temp)
    current_weather = [temp_forecast, precipitation_forecast]

    #### User info
    query = """
    MATCH (a: Person {name: $user_name})
    RETURN a
    """
    user_profile_data = neo4j.query_graph(query, DATABASE, ['a'], {"user_name": user_name})
    print(user_profile_data)

    vo2max = user_profile_data[0][0]['vo2max']
    additional_reqs = user_profile_data[0][0]['additional_requirements']

    query = """
    MATCH (n:Person {name: $user_name})-[:HAS_EQUIPMENT]->(e:Equipment)
    RETURN e.EQ_name
    """

    available_eq = neo4j.query_graph(query, DATABASE, ['e.EQ_name'], {"user_name": user_name})[0]
    #print(available_eq)

    #### Coaching styles

    query = """
    MATCH (p:Person {name: $user_name})-[:HAS_PREFERENCE]->(n:sub_style)<-[:HAS_SUBTYPE]-(c:Coaching_style) 
    RETURN n;
    """

    coaching_style = neo4j.query_graph(query=query, database=DATABASE, return_chars=['n'], parameters={"user_name": user_name})

    coaching_style_preferences = {}
    tones = []
    tone_descriptors = []

    for style in coaching_style[0]:
            if "tone" in style['substyleID']:
                tones.append(style['Style_type'])
                tone_descriptors.append(style['Description'])
            else:
                coaching_style_preferences["support"] = f"{style['Style_type']} support - " + style['Description']
            
    coaching_style_preferences['tone of voice'] = f"{" and ".join(tones)} tone of voice (being {" and ".join(tone_descriptors)})"
    #print(coaching_style_preferences)

    #### Barriers
    query = """
    MATCH (p:Person {name: $user_name})-[:HAS_BARRIER]->(b:Barrier)-[:HAS_SOLUTION]->(c:Coping_strategy) 
    RETURN DISTINCT c,b
    """

    user_barriers = neo4j.query_graph(query=query, database=DATABASE, return_chars=['b','c'], parameters={"user_name": user_name})

    choose_coping_strategy = randint(0, len(user_barriers[0])-1)
    coping_strategy = user_barriers[1][choose_coping_strategy]['Instance_solution']
    barrier = user_barriers[0][choose_coping_strategy]['Instance_barrier']

    #### Vo2max + mpa
    met_mpa_lower = round(vo2max / 8.75,1)
    met_mpa_higher = round(vo2max / 6, 1)
    met_vpa_higher = round(vo2max/4.17, 1)

    #### Get activities
    if location_restriction == 1:
        location = ["indoor", "indoor/outdoor"]
    else:
        location = ["indoor", "indoor/outdoor", "outdoor"]

    if user_profile == "CG":
        query="""
        MATCH (p:Person {name: $user_name})-[:HAS_PREFERENCE]->(s:Sport)-[:HAS_ACTIVITY]->(a:Activity)
        WHERE a.METs <= $mets_boundary_higher
        AND a.Location IN $location
        AND a.Equipment IN $available_eq
        RETURN  DISTINCT a
        ORDER BY a.METs
        """
        mets_top = met_mpa_lower
        #Fetch activities from the KG
        recommendations = neo4j.query_graph(query, DATABASE, ['a'], {'user_name': user_name, 'mets_boundary_higher': mets_top, 'location':location, 'available_eq': available_eq})
        

    if user_profile == "WF":
        query="""
        MATCH (p:Person {name: $user_name})-[:HAS_PREFERENCE]->(s:Sport)-[:HAS_ACTIVITY]->(a:Activity)
        WHERE a.METs <= $mets_boundary_higher
        AND a.Location IN $location
        AND a.Equipment IN $available_eq
        RETURN  DISTINCT a
        ORDER BY a.METs
        """
        mets_top = met_vpa_higher
        #Fetch activities from the KG
        recommendations = neo4j.query_graph(query, DATABASE, ['a'], {'user_name': user_name, 'mets_boundary_higher': mets_top, 'location':location, 'available_eq': available_eq})


    if user_profile == "SM":
        query="""
        MATCH (p:Person {name: $user_name})-[:HAS_PREFERENCE]->(s:Sport)-[:HAS_ACTIVITY]->(a:Activity)
        WHERE a.olderAdult = TRUE
        AND a.METs <= $mets_boundary_higher
        AND a.METs >= $mets_boundary_lower
        AND a.Location IN $location
        AND a.Equipment IN $available_eq
        RETURN  DISTINCT a
        ORDER BY a.METs
        """
        mets_top = met_mpa_higher
        mets_bottom = met_mpa_lower

        #Fetch activities from the KG
        recommendations = neo4j.query_graph(query, DATABASE, ['a'], {'user_name': user_name, 'mets_boundary_higher': mets_top, 'mets_boundary_lower': mets_bottom, 'location':location, 'available_eq': available_eq})

    #### Refiner
    target_time = mpa_goal - user_activity['mpa']

    if user_profile == "CG" or user_profile == "SM":
        refined_recs = []
        sample_size = 1
        if len(recommendations[0]) > 2:
            sample_size = 3
        rec_sampling = sample(range(0,len(recommendations[0])), sample_size)

        for i in rec_sampling:
            chosen_recs = recommendations[0][i]

            if chosen_recs['intensity'] != "NA":
                refined_recs.append(f"activity: {chosen_recs['subtype']}, intensity: {assign_intensity(chosen_recs['METs'])}, {chosen_recs['intensity']}, location: {chosen_recs['Location']}, equipment:{chosen_recs['Equipment']}\n")
            else: 
                refined_recs.append(f"activity: {chosen_recs['subtype']}, intensity: {assign_intensity(chosen_recs['METs'])}, location:{chosen_recs['Location']}, equipment:{chosen_recs['Equipment']}\n")



    if user_profile == "WF":
        refined_recs = []

        sample_size = 1
        rec_sampling = sample(range(0,len(recommendations[0][:-3])), sample_size)
    
        for i in rec_sampling:
            chosen_recs = recommendations[0][i]
    
            if chosen_recs['intensity'] != "NA":
                refined_recs.append(f"activity: {chosen_recs['subtype']}, intensity: {assign_intensity(chosen_recs['METs'])}, {chosen_recs['intensity']}, location: {chosen_recs['Location']}, equipment:{chosen_recs['Equipment']}\n")
            else: 
                refined_recs.append(f"activity: {chosen_recs['subtype']}, intensity: {assign_intensity(chosen_recs['METs'])}, location:{chosen_recs['Location']}, equipment:{chosen_recs['Equipment']}\n")
    
        challenge = recommendations[0][-3:]
        challenge_sampling = sample(range(0,(len(challenge))), 2)
        for i in challenge_sampling:
            chosen_recs = challenge[i]
            if chosen_recs['intensity'] != "NA":
                refined_recs.append(f"activity for a challenge: {chosen_recs['subtype']}, intensity: {assign_intensity(chosen_recs['METs'])}, {chosen_recs['intensity']}, location: {chosen_recs['Location']}, equipment:{chosen_recs['Equipment']}\n")
            else: 
                refined_recs.append(f"activity for a challenge: {chosen_recs['subtype']}, intensity: {assign_intensity(chosen_recs['METs'])}, location:{chosen_recs['Location']}, equipment:{chosen_recs['Equipment']}\n")
    print(refined_recs)    

    #### Make prompt
    if location_restriction == -1:
        prompt = f"""
                For your current user {user_alias}, use {coaching_style_preferences['tone of voice']} when writing your recommendations. Your coaching style must exhibit {coaching_style_preferences['support']}
        
                [CONTENT] The weather right now is: {current_weather}. It is too hot to be very active, therefore, you should recommend the user to reduce their physical activity for the time being
                and to remain hydrated. 
        
                Keep the length of the message under {message_length} words.
                {additional_reqs}
                """
    elif location_restriction == 1:
        prompt = f"""
            For your current user {user_alias}, use {coaching_style_preferences['tone of voice']} when writing your recommendations. Your coaching style must exhibit {coaching_style_preferences['support']} 
    
            [CONTENT] Write a short recommendation in the form of a notification message, based on the following content points (1-5): 
    
            1. Activities to recommend that the user can choose from (use a bullet-point list to format the list of activities and include the activity intensity and equipment, if any is required): 
            - {" - ".join(refined_recs)}
    
            2. The user needs to be active for at least {target_time} minutes to reach their goal. 
    
            3. The recommended activities have the appropriate intensity for the current fitness level of the user that will help them reach their physical activity goals.
    
            4. Current weather: {current_weather}. With this temperature, activity should be restricted to indoors.
    
            5. The user tends to experience this barrier: {barrier}. Suggest the following as a coping strategy for that barrier: {coping_strategy}. 
    
            Keep the length of the message under {message_length} words.
            {additional_reqs}
            """
    else:
        prompt = f"""
            For your current user {user_alias}, use {coaching_style_preferences['tone of voice']} when writing your recommendations. Your coaching style must exhibit {coaching_style_preferences['support']} 

            [CONTENT] Write a short recommendation in the form of a notification message, based on the following content points (1-5): 

            1. Activities to recommend that the user can choose from (use a bullet-point list to format the list of activities and include the activity intensity and equipment, if any is required): 
            - {" - ".join(refined_recs)}

            2. The user needs to be active for at least {target_time} minutes to reach their goal. 

            3. The recommended activities have the appropriate intensity for the current fitness level of the user that will help them reach their physical activity goals.

            4. Current weather: {current_weather}.

            5. The user tends to experience this barrier: {barrier}. Suggest the following as a coping strategy for that barrier: {coping_strategy}. 
            
            Keep the length of the message under {message_length} words.
            {additional_reqs}
            """

    sys_prompt = """
                [ROLE] Take on the role of a digital lifestyle coach to provide the user with activity recommendations that are personalized to their physical capabilities, activity type preferences and contextual variables, such as the weather and their activity data. 
                [CONSTRAINTS] Make sure to write the message in simple language. Do not include any other text in your response besides the message. Do not try to insert any variables or information that you do not have access to. The user cannot respond to you, so do not try to chat with them."""
    full_prompt = sys_prompt + prompt

    prompt_data.loc[len(prompt_data)] = [user_name, sys_prompt, prompt, full_prompt]


neo4j.close_driver()

prompt_data.to_excel("src\\prompt_data.xlsx")


