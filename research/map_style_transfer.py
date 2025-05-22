import re
import os
import time
import json
import base64
import argparse
import requests
from openai import OpenAI
from collections import defaultdict
from utils.prompt import IMAGE_APPRECIATOR, STYLESHEET_DESIGNER, MAP_REVIEWER

# === Step Functions ===
def initialize_args():
    parser = argparse.ArgumentParser(description="Map style transfer.")
    parser.add_argument('--api_key', required=True, help='Your OpenAI API key')
    parser.add_argument('--mapbox_token', required=True, help='Your Mapbox token')
    parser.add_argument('--mapbox_username', required=True, help='Your Mapbox username')
    parser.add_argument('--inspiration_path', required=True, help='Path to the inspiration image')
    parser.add_argument('--map_data_path', required=True, help='Path to the map data JSON')
    parser.add_argument('--output_dir', default='./results', help='Directory to save results')
    return parser.parse_args()

def ensure_output_dir(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    return {
        'save_format': os.path.join(output_dir, '{0}_{1}.png'),
        'log': os.path.join(output_dir, 'log.txt')
    }

def upload_map_data(map_data_path, mapbox_token, mapbox_username):
    with open(map_data_path, 'r') as f:
        style_json = json.load(f)
    data_name = style_json['name']
    print_parameters = {
        'width': style_json['metadata']['mapbox:print']['width'],
        'height': style_json['metadata']['mapbox:print']['height'],
        'resolution': style_json['metadata']['mapbox:print']['resolution'],
        'longitude': style_json['center'][0],
        'latitude': style_json['center'][1],
        'zoom': style_json['zoom']
    }
    url = f"https://api.mapbox.com/styles/v1/{mapbox_username}?access_token={mapbox_token}"
    headers = {
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(url, headers=headers, json=style_json)
        result = response.json()
        style_id = result['id']
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    return style_json, data_name, print_parameters, style_id

def process_map_data(map_data_path, mapbox_token, mapbox_username):
    style_json, data_name, print_parameters, style_id = upload_map_data(map_data_path, mapbox_token, mapbox_username)
    print("✓ Map data uploaded.")
    return style_json, data_name, print_parameters, style_id

def download_map_image(save_path, print_parameters, style_id, mapbox_token, mapbox_username):
    url = f'https://api.mapbox.com/styles/v1/{mapbox_username}/{style_id}/static/{print_parameters["longitude"]},{print_parameters["latitude"]},{print_parameters["zoom"]}/{print_parameters["width"]}x{print_parameters["height"]}?access_token={mapbox_token}'
    try:
        response = requests.get(url)
        with open(save_path, "wb") as file:
            file.write(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

def download_initial_map_image(data_name, print_parameters, style_id, mapbox_token, mapbox_username, save_format):
    path = save_format.format(data_name, 'origin')
    download_map_image(path, print_parameters, style_id, mapbox_token, mapbox_username)
    print("✓ Original map image downloaded.")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def image_appreciation(inspiration_path, client, chat_model, log_path, max_retries=5, delay=2):
    base64_image = encode_image(inspiration_path)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model = chat_model,
                messages = [
                    {"role": "user", "content": [{"type": "text", "text": IMAGE_APPRECIATOR}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "OK"}]},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}
                ]
            )
            ans = response.choices[0].message.content
            with open(log_path, 'a', encoding = 'utf-8') as f:
                f.write('-'*20 + '\n')
                f.write("Image Appreciation: \n")
                f.write('User: ' + IMAGE_APPRECIATOR + '\n')
                f.write('Assistant: OK.\n')
                f.write('User: <image>.\n')
                f.write('Assistant: ' + ans + '\n')
            return ans
        except Exception as e:
            print(f"Error making API call (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached. Exiting.")
                return None

def generate_image_caption(inspiration_path, client, model, log_path):
    caption = image_appreciation(inspiration_path, client, model, log_path)
    print("✓ Image caption generated.")
    return caption

def stylesheet_design(data_name, style_json, inspiration_path, image_caption, client, chat_model, log_path, max_retries=5, delay=2):
    type_dict = defaultdict(list)
    layers = style_json['layers']
    for layer in layers:
        layer_name = layer['id']
        if 'layout' in layer and 'icon-image' in layer['layout']:
            layer_type = layer['type'] + '_icon'
        elif 'layout' in layer:
            layer_type = layer['type'] + '_label'
        else:
            layer_type = layer['type']
        layer_properties = list(layer['paint'].keys())
        type_dict[layer_type].append({
            'name': layer_name,
            'properties': layer_properties
        })
    
    map_elements = ""
    for k, values in type_dict.items():
        values = [v['name'] for v in values]
        map_elements += '• {} elements: {}.\n'.format(k, ', '.join(values))

    requirements = ""
    for k, values in type_dict.items():
        values = [properties for v in values for properties in v['properties']]
        values = list(set(values))
        if k == 'symbol_icon':
            requirements += '• For each {} element, you can describe the expected style in as much detail as possible, e.g., its content, color, theme, and design. The icon designer will design this icon according to your expectations;\n'.format(k)
        else:
            requirements += '• For each {} element, you can set the {}.\n'.format(k, ', '.join(values))

    format_string = "\n{\n"
    format_string += '    "reasoning": ...,\n'
    format_string += '    "stylesheet": {\n'
    for k, values in type_dict.items():
        format_string += '        "{}": {{\n'.format(k)
        for value in values:
            if k == 'symbol_icon':
                format_string += '            "{}": {{"explanation": ..., "expectation": ...}},\n'.format(value['name'])
            else:
                properties = value['properties']
                format_string += '            "{}": {{'.format(value['name'])
                format_string += '"explanation": ..., '
                for prop in properties:
                    format_string += '"' + prop + '": ..., '
                format_string += '},\n'
        format_string += '        },\n'
    format_string += "    }\n"
    format_string += "}\n"

    base64_image = encode_image(inspiration_path)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model = chat_model,
                messages = [
                    {"role": "user", "content": [{"type": "text", "text": STYLESHEET_DESIGNER.format(map_elements,requirements,format_string)}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "OK"}]},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "I have received the reference image, please upload the description."}]},
                    {"role": "user", "content": [{"type": "text", "text": "[Description]:\n" + image_caption + '\nRemember just return the JSON file.'}]}
                ]
            )
            json_string = response.choices[0].message.content
            json_str = re.search(r'```json(.*?)```', json_string, re.DOTALL).group(1)
            with open(log_path, 'a', encoding = 'utf-8') as f:
                f.write('-'*20  + '\n')
                f.write("Stylesheet Design: \n")
                f.write('User: ' + STYLESHEET_DESIGNER.format(map_elements,requirements,format_string) + '\n')
                f.write('Assistant: OK.\n')
                f.write('User: <image>.\n')
                f.write('Assistant: I have received the reference image, please upload the description.\n')
                f.write('User: [Description]:\n' + image_caption + '\nRemember just return the JSON file.\n')
                f.write('Assistant: ' + json_str + '\n')
            try:
                data = json.loads(json_str.strip())
                return data
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                return None
        except Exception as e:
            print(f"Error making API call (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached. Exiting.")
                return None

def update_stylesheet(stylesheet, style_json, mapbox_username, mapbox_token):
    element2id = {}
    for i in range(len(style_json['layers'])):
        element2id[style_json['layers'][i]['id']] = i

    if 'stylesheet' in stylesheet:
        stylesheet = stylesheet['stylesheet']
    for tp, element_dict in stylesheet.items():
        if tp != 'symbol_icon':
            for element, property_dict in element_dict.items():
                if element in element2id:
                    for property_key, property_value in property_dict.items():
                        if property_key in style_json['layers'][element2id[element]]['paint']:
                            paint_property = style_json['layers'][element2id[element]]['paint'][property_key]
                            if isinstance(paint_property, list) and len(paint_property) == 5:
                                style_json['layers'][element2id[element]]['paint'][property_key][3] = property_value
                            else:
                                style_json['layers'][element2id[element]]['paint'][property_key] = property_value
    
    url = f"https://api.mapbox.com/styles/v1/{mapbox_username}?access_token={mapbox_token}"
    headers = {
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(url, headers=headers, json=style_json)
        result = response.json()
        style_id = result['id']
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

    return style_json, style_id

def design_and_update_stylesheet(data_name, style_json, inspiration_path, image_caption, client, model, log_path, mapbox_username, mapbox_token, save_format, print_parameters):
    stylesheet = stylesheet_design(data_name, style_json, inspiration_path, image_caption, client, model, log_path)
    print("✓ Stylesheet designed.")
    updated_style_json, new_style_id = update_stylesheet(stylesheet, style_json, mapbox_username, mapbox_token)
    print("✓ Style sheet updated.")
    download_map_image(save_format.format(data_name, 'R1'), print_parameters, new_style_id, mapbox_token, mapbox_username)
    print("✓ Updated map image downloaded.")
    return updated_style_json, new_style_id

def map_evaluation(style_json, map_path, inspiration_path, client, chat_model, log_path, max_retries=5, delay=2):
    type_dict = defaultdict(list)
    layers = style_json['layers']
    for layer in layers:
        layer_name = layer['id']
        if 'layout' in layer and 'icon-image' in layer['layout']:
            continue
        elif 'layout' in layer:
            layer_type = layer['type'] + '_label'
        else:
            layer_type = layer['type']
        layer_properties = list(layer['paint'].keys())
        type_dict[layer_type].append({
            'name': layer_name,
            'properties': layer_properties
        })

    map_elements = ""
    for k, values in type_dict.items():
        values = [v['name'] for v in values]
        map_elements += '• {} elements: {}.\n'.format(k, ', '.join(values))

    requirements = ""
    for k, values in type_dict.items():
        values = [properties for v in values for properties in v['properties']]
        values = list(set(values))
        requirements += '• For each {} element, you can change the {}.\n'.format(k, ', '.join(values))

    format_string = "{\n"
    format_string += '    "Action": "Revision",\n'
    format_string += '    "Modified style sheet": {\n'
    for k, values in type_dict.items():
        format_string += '        "{}": {{\n'.format(k)
        for value in values:
            properties = value['properties']    
            format_string += '            "{}": {{'.format(value['name'])    
            for prop in properties:
                format_string += '"' + prop + '": ..., '
            format_string += '},\n'
        format_string += '        },\n'
    format_string += "    }\n}\n"
    
    base64_inspiration = encode_image(inspiration_path)
    base64_map = encode_image(map_path)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model = chat_model,
                messages = [
                    {"role": "user", "content": [{"type": "text", "text": MAP_REVIEWER.format(map_elements, requirements, format_string)}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "OK"}]},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_inspiration}"}}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "I have received the reference image, please upload the map."}]},
                    {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_map}"}}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "I have received the map."}]},
                    {"role": "user", "content": [{"type": "text", "text": "Please provide your answer. Since maps also need to convey information effectively, it is not necessary for two images to have exactly the same style. Remember just return the JSON file, and note that you do not need to modify all map elements."}]},
                ]
            )
            json_string = response.choices[0].message.content
            json_str = re.search(r'```json(.*?)```', json_string, re.DOTALL).group(1)
            with open(log_path, 'a', encoding = 'utf-8') as f:
                f.write('-'*20  + '\n')
                f.write("Map evaluation: \n")
                f.write('User: ' + MAP_REVIEWER.format(map_elements, requirements, format_string) + '\n')
                f.write('Assistant: OK.\n')
                f.write('User: <image>.\n')
                f.write('Assistant: I have received the reference image, please upload the map.\n')
                f.write('User: <image>.\n')
                f.write('Assistant: I have received the map.\n')
                f.write('User: Please provide your answer. Since maps also need to convey information effectively, it is not necessary for two images to have exactly the same style. Remember just return the JSON file, and note that you do not need to modify all map elements.\n')
                f.write('Assistant: ' + json_str + '\n')
            try:
                data = json.loads(json_str.strip())
                return data
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                continue
        except Exception as e:
            print(f"Error making API call (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached. Exiting.")
                return None

def iterative_evaluation(style_json, data_name, inspiration_path, client, model, log_path, mapbox_username, mapbox_token, save_format, print_parameters, style_id):
    iteration = 1
    while True:
        image_path = save_format.format(data_name, f'R{iteration}')
        comments = map_evaluation(style_json, image_path, inspiration_path, client, model, log_path)
        print(f"✓ Map evaluation R{iteration} completed.")
        
        if comments.get("Action") == 'Accept':
            print("✓ Final style accepted.")
            break

        iteration += 1
        style_json, style_id = update_stylesheet(comments["Modified style sheet"], style_json, mapbox_username, mapbox_token)
        print(f"✓ Style updated for R{iteration}.")
        download_map_image(save_format.format(data_name, f'R{iteration}'), print_parameters, style_id, mapbox_token, mapbox_username)
        print(f"✓ Map image R{iteration} downloaded.")

# === Main Function ===
def main():
    args = initialize_args()
    paths = ensure_output_dir(args.output_dir)
    client = OpenAI(api_key=args.api_key)
    chat_model = 'gpt-4o'

    # Step 1: Upload map data
    style_json, data_name, print_parameters, style_id = process_map_data(args.map_data_path, args.mapbox_token, args.mapbox_username)

    # Step 2: Download original map
    download_initial_map_image(data_name, print_parameters, style_id, args.mapbox_token, args.mapbox_username, paths['save_format'])

    # Step 3: Image appreciation
    image_caption = generate_image_caption(args.inspiration_path, client, chat_model, paths['log'])

    # Step 4: Design and update stylesheet
    style_json, style_id = design_and_update_stylesheet(data_name, style_json, args.inspiration_path, image_caption, client, chat_model, paths['log'], args.mapbox_username, args.mapbox_token, paths['save_format'], print_parameters)

    # Step 5+: Evaluation loop
    iterative_evaluation(style_json, data_name, args.inspiration_path, client, chat_model, paths['log'], args.mapbox_username, args.mapbox_token, paths['save_format'], print_parameters, style_id)

# === Entry Point ===
if __name__ == '__main__':
    main()