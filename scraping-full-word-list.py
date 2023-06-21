import time
import requests
from bs4 import BeautifulSoup
import json
import sys
import subprocess
import sys
# URL to scrape
url = 'https://www.englishprofile.org/wordlists/evp'


def clear_title(title):
    m_string = title
    inside_of_paranthesis = ''
    if '(' in m_string and ')' in m_string:
        inside_of_paranthesis =  m_string.split('(')[1].split(')')[0]
        if inside_of_paranthesis.isupper() or len(inside_of_paranthesis) == 0:
            m_string = m_string.split(' (')[0]
        else:
            inside_of_paranthesis = ''
    
    return m_string, inside_of_paranthesis

# define payload for search post request
# custom_levels [A1, A2, B1, B2, C1, C2]
# custom_levels [1,  2,  3,  4,  5,  6]
custom_levels = [6]
payload = {
    "filter_search": "",
    "filter_custom_Level[]": custom_levels,
    "filter_order": "base", # base = word
    "sortTable": "base",
    "filter_order_Dir": "asc",
    "directionTable": "asc",
    "limit": 10000,
}

# make post request to url
r = requests.post(url, data=payload)
soup = BeautifulSoup(r.text, 'html.parser')

# find report table
report_table_div = soup.find('div', {'class': 'report-table'})
report_table = report_table_div.find('table')
# take search rows
rows = report_table.find('tbody').find_all('tr')

# create word list
words_list = []
for idx, row in enumerate(rows):
    word_cells = row.find_all('td') # first cell
    word_cell = word_cells[0]
    level_cell = word_cells[2]
    type_cell = word_cells[3]
    detail_link_cell = word_cells[5]
    raw_word = (word_cell.text).strip()
    raw_type = type_cell.text
    raw_level = level_cell.text
    raw_detail_link = detail_link_cell.find('a')['href']
    detail_link = url.replace("/wordlists/evp", "") + raw_detail_link
    word_list_element_cooked = {
        "word": raw_word,
        "type": raw_type,
        "level": raw_level,
        "link": detail_link,
    }
    if word_list_element_cooked not in words_list:
        words_list.append(word_list_element_cooked)

# go into detail page for each word
scanning_count = 0
for word in words_list:
    # go into detail page
    detail_page = requests.get(word['link'])
    detail_soup = BeautifulSoup(detail_page.text, 'html.parser')
    # find type_section divs
    raw_type_sections = detail_soup.find_all('div', {'class': 'pos_section'})
    # all detail elements
    all_detail_elements = detail_soup.find_all('div', {'class': 'info sense'})
    # cook info elements by type sections
    # [title: word, type: noun, level: A1, descriptions: [aaa], meanings: [bbb], examples: [[ccc, ddd]]]
    list_by_type = []
    for idx, type_section in enumerate(raw_type_sections):
        word_type = type_section.find('span', {'class': 'pos'}).text
        
        info_elements_in_type = type_section.find_all('div', {'class': 'info sense'})
        # unmerged list by title and level
        infos_in_type = []
        for info_element in info_elements_in_type:
            title = info_element.find('div', {'class': 'sense_title'}).text
            level = info_element.find('span', {'class': 'label'}).text
            meaning = info_element.find('span', {'class': 'definition'}).text
            raw_example_element = info_element.find('div', {'class': 'example'})
            if raw_example_element is not None:
                raw_examples = raw_example_element.find_all("p", {'class': 'blockquote'})
            else:
                raw_examples = []
            examples = []
            for raw_example in raw_examples:
                example = raw_example.text
                examples.append(example)
            
            info_element_cooked = {
                "title": title,
                "type": word_type,
                "level": level,
                "meanings": [meaning],
                "examples": [examples],
            }
            infos_in_type.append(info_element_cooked)
            all_detail_elements.remove(info_element)
        # merge infos in type
        merged_info_titles = []
        merged_infos_in_type = []
        for info in infos_in_type:
            uncleared_title = info['title']
            cleared_title = clear_title(uncleared_title)[0]
            hint = clear_title(uncleared_title)[1]
            info["title"] = cleared_title
            if hint != '':
                info["hints"] = [hint]
            else:
                info["hints"] = []
            
            comparison_element = {
                "title": cleared_title,
                "level": info["level"],
            }
            if comparison_element not in merged_info_titles:
                merged_infos_in_type.append(info)
                merged_info_titles.append(comparison_element)
            else:
                for merged_info in merged_infos_in_type:
                    if merged_info['title'] == cleared_title:
                        merged_info['examples'] += info['examples']
                        merged_info['meanings'] += info['meanings']
                        merged_info['hints'] += info['hints']

        for merged_info in merged_infos_in_type:
            if word["word"] == merged_info["title"] and word["level"] == merged_info["level"] and (word["type"] == merged_info["type"] or word["type"] == "phrase"):
                list_by_type.append(merged_info)
        
    if len(list_by_type) == 1:
        word["meanings"] = list_by_type[0]["meanings"]
        word["examples"] = list_by_type[0]["examples"]
        word["hints"] = list_by_type[0]["hints"]
    elif len(list_by_type) == 0:
        # take it from outside of type sections
        unmerged_list_by_type = []
        for element in all_detail_elements:
            title = element.find('div', {'class': 'sense_title'}).text
            level = element.find('span', {'class': 'label'}).text
            meaning = element.find('span', {'class': 'definition'}).text
            raw_example_element = info_element.find('div', {'class': 'example'})
            if raw_example_element is not None:
                raw_examples = raw_example_element.find_all("p", {'class': 'blockquote'})
            else:
                raw_examples = []
            examples = []
            for raw_example in raw_examples:
                example = raw_example.text
                examples.append(example)
            
            info_element_cooked = {
                "title": title,
                "type": "None",
                "level": level,
                "meanings": [meaning],
                "examples": [examples],
            }
            unmerged_list_by_type.append(info_element_cooked)
        # merge infos in type
        merged_info_titles = []
        merged_infos_in_type = []
        for info in unmerged_list_by_type:
            uncleared_title = info['title']
            cleared_title = clear_title(uncleared_title)[0]
            hint = clear_title(uncleared_title)[1]
            info["title"] = cleared_title
            if hint != '':
                info["hints"] = [hint]
            else:
                info["hints"] = []
            
            comparison_element = {
                "title": cleared_title,
                "level": info["level"],
            }
            if comparison_element not in merged_info_titles:
                merged_infos_in_type.append(info)
                merged_info_titles.append(comparison_element)
            else:
                for merged_info in merged_infos_in_type:
                    if merged_info['title'] == cleared_title:
                        merged_info['examples'] += info['examples']
                        merged_info['meanings'] += info['meanings']
                        merged_info['hints'] += info['hints']
        for merged_info in merged_infos_in_type:
            if word["word"] == merged_info["title"] and word["level"] == merged_info["level"] and (word["type"] == merged_info["type"] or word["type"] == "phrasal verb"):
                list_by_type.append(merged_info)
        if len(list_by_type) == 1:
            word["meanings"] = list_by_type[0]["meanings"]
            word["examples"] = list_by_type[0]["examples"]
            word["hints"] = list_by_type[0]["hints"]
        else:
            print("ERROR: Couldn't find any type section for this word: " + word["word"])
    else:
        print("ERROR: There are more than one type section for this word: " + word["word"])
    
    scanning_count = scanning_count + 1
    sys.stdout.write('\033[K' + f"{scanning_count} of {len(words_list)} scanned. last: { word['word']}" + '\r')

print(len(words_list))
# save word_list to json file
with open('C2.json', 'w') as outfile:
    # json.dump(words_list, outfile, ensure_ascii=False, indent=4)
    outfile.write("[\n")
    for idx, obj in enumerate(words_list):
        if obj["type"] != "" and "meanings" in obj.keys():
            if idx == len(words_list) - 1:
                outfile.write(json.dumps(obj) + "\n")
            else:
                outfile.write(json.dumps(obj) + ",\n")
        else:
            print("ERROR: This word has not type or meaning: " + obj["word"] + " type: " + obj["type"] + ". and skipped")
    outfile.write("]\n")
