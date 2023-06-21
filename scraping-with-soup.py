import time
import requests
from bs4 import BeautifulSoup
import json
import sys
import subprocess
# URL to scrape
url = 'https://www.englishprofile.org/wordlists/evp'

def look_into_detail_header(m_string):
    # if there is string in paranthesis, return it
    inside_of_paranthesis = ''
    if '(' in m_string and ')' in m_string:
        inside_of_paranthesis =  m_string.split('(')[1].split(')')[0]
        if inside_of_paranthesis.isupper() or len(inside_of_paranthesis) == 0:
            m_string = m_string.split(' (')[0]

    
    m_string = m_string.replace(", etc.", "")
    
    return m_string, inside_of_paranthesis

# print("result", look_into_detail_header('come (COME, WITH)'))

missing_count = 0
last_missing_word = ''
def search_word(word, level):
    try:
        # Levels [1, 2, 3, 4, 5]
        # levels_w = [A1, A2, B1, B2, C1, C2]
        search_word = word
        search_word = search_word.replace(", etc.", "")
        filter_custom_level = [1, 2, 3, 4, 5]
        filter_order = 'base' # base = word
        sortTable = 'base'
        filter_order_Dir = "asc"
        directionTable = "asc"
        limit = 1000
        payload = {
            "filter_search": search_word,
            "filter_custom_Level[]": filter_custom_level,
            "filter_order": filter_order, # base = word
            "sortTable": sortTable,
            "filter_order_Dir": filter_order_Dir,
            "directionTable": directionTable,
            "limit": limit,
        }

        # make post request to url
        r = requests.post(url, data=payload)
        soup = BeautifulSoup(r.text, 'html.parser')

        # find report table
        report_table_div = soup.find('div', {'class': 'report-table'})
        report_table = report_table_div.find('table')
        rows = report_table.find('tbody').find_all('tr')
        #print("rows: ", len(rows))

        # eliminate rows that are not exact match
        exact_word_rows = []
        for row in rows:
            cells = row.find_all('td')
            cell_text = cells[0].text
            cell_text = cell_text.strip()
            cell_text = cell_text.replace(", etc.", "")
            # print("cells: ", cell_text, "search_word: ", search_word)
            # print("cell_text == search_word: ", cell_text == search_word)
            # print(len(cell_text), len(search_word))
            if cell_text == search_word:
                exact_word_rows.append(row)

        # get inside of search result
        results_cooked = []
        #print("exact_word_rows: ", exact_word_rows)
        # get details in firs element's link
        first_element_link = url.replace("/wordlists/evp", "") + exact_word_rows[0].find('a', {'class': 'btn btn-info btn-large'})['href']
        #print("first_element_link: ", first_element_link)
        r2 = requests.get(first_element_link)
        soup2 = BeautifulSoup(r2.text, 'html.parser')
        # find all type sections
        type_sections = soup2.find_all('div', {'class': 'pos_section'})
        # for looop for type sections
        collected_info_elements = []
        for type_section in type_sections:
            exact_info_elements = []
            word_type = type_section.find('span', {'class': 'pos'}).text
            all_info_elements = soup2.find_all('div', {'class': 'info sense'})
            info_elements = type_section.find_all('div', {'class': 'info sense'})
            
            for info_element in info_elements:
                info_element_title = info_element.find('div', {'class': 'sense_title'})
                # remove info elements in type section from all_info_elements
                if info_element in all_info_elements:
                    all_info_elements.remove(info_element)

                #print("info element title: ", look_into_detail_header(info_element_title.text)[0])
                #print("search_word: ", search_word, "function_coming", look_into_detail_header(info_element_title.text)[0], "function_going", info_element_title.text)
                if look_into_detail_header(info_element_title.text)[0] == search_word:
                    exact_info_elements.append(info_element)
            
            # if there is no element found in type sections, look into all info elements
            if len(exact_info_elements) == 0:
                for all_info_element in all_info_elements:
                    all_info_element_title = all_info_element.find('div', {'class': 'sense_title'})
                    if look_into_detail_header(all_info_element_title.text)[0] == search_word:
                        exact_info_elements.append(all_info_element)
                        word_type = "phrasal verb"

            info_elements_cooked = []
            for exact_info_element in exact_info_elements:
                exact_info_element_title = exact_info_element.find('div', {'class': 'sense_title'}).text
                exact_info_element_level = exact_info_element.find('span', {'class': 'label'}).text
                exact_info_element_definition = exact_info_element.find('span', {'class': 'definition'}).text
                exact_info_element_type = word_type
                exact_info_element_examples = exact_info_element.find('div', {'class': 'example'}).find_all("p", {'class': 'blockquote'})
                exact_info_element_examples_cooked = []
                for exact_info_element_example in exact_info_element_examples:
                    exact_info_element_examples_cooked.append(exact_info_element_example.text)

                (exact_info_element_title, exact_info_element_description) = look_into_detail_header(exact_info_element_title)
                if exact_info_element_level == level:
                    info_element_cooked = {
                        "title": exact_info_element_title,
                        "type": exact_info_element_type,
                        "description": exact_info_element_description,
                        "level": exact_info_element_level,
                        "definition": exact_info_element_definition,
                        "examples": exact_info_element_examples_cooked
                    }
                    info_elements_cooked.append(info_element_cooked)
            
            # print("info elements cooked: ")
            for info_element_cooked in info_elements_cooked:
                collected_info_elements.append(info_element_cooked)
                # print(info_element_cooked)
        #print("collected_info_elements: ", collected_info_elements)
        elements_cooked = []
        """ [{
            'word': 'example',
            'type': 'noun',
            'level': 'A1',
            'descriptions': ["first description", "second description"],
            'definitions': ["first definition", "second definition"],
            'examples': [["first of first example", "second of first example]], ["firt of second example"]]
        # }]
        """
        element_types_inserted = []
        for element in collected_info_elements:
            if element['type'] not in element_types_inserted:
                element_cooking = {
                    'word': element['title'],
                    'type': element['type'],
                    'level': element['level'],
                    'descriptions': [element['description']],
                    'definitions': [element['definition']],
                    'examples': [element['examples']]
                }
                elements_cooked.append(element_cooking)
                element_types_inserted.append(element['type'])
            else:
                for element_cooked in elements_cooked:
                    if element_cooked['type'] == element['type']:
                        element_cooked['descriptions'].append(element['description'])
                        element_cooked['definitions'].append(element['definition'])
                        element_cooked['examples'].append(element['examples'])
                        break
        
        # for element in elements_cooked:
        #     print('Word: ', element['word'], 'Type: ', element['type'], 'Level: ', element['level'])
        #     print('Description: ', element['descriptions'])
        #     print('Definition: ', element['definitions'])
        #     print('Examples: ', element['examples'])
        #     print('------------------')

        return elements_cooked
    except Exception as e:
        #print("Error: ", e)
        global missing_count
        global last_missing_word
        missing_count = missing_count + 1
        last_missing_word = search_word
        return []

def take_and_cook(reading_json_file, writing_json_file, missing_json_file):
    # import json as my_words
    my_words = []
    # read my_words from Words.json
    with open('missing_words.json') as json_file:
        my_words = json.load(json_file)

    my_token_words = []
    my_missing_words = []
    for idx, my_word in enumerate(my_words):
        print(f"{idx} of {len(my_words)} taking... {missing_count} missing. last missing: {last_missing_word}", end="\r")
        results_cooked = search_word(my_word["Word"], my_word["Level"])
        if len(results_cooked) > 0:
            my_token_words.append(results_cooked)
        else:
            my_missing_words.append(my_word)
        
        #time.sleep(1)

    # save my_token_words to token_words.json
    with open('token_words2.json', 'w') as outfile:
        json.dump(my_token_words, outfile)

    # save my_missing_words to missing_words.json
    with open('missing_words2.json', 'w') as outfile:
        json.dump(my_missing_words, outfile)

    print("files saved successfully. token words: ", len(my_token_words), " missing words: ", len(my_missing_words))

take_and_cook('missing_words.json', 'token_words2.json', 'missing_words2.json')

#print(search_word("call for sb", "B1"))