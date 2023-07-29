import csv
import json
import re
import sys

import colorama
import pyperclip
import requests
from bs4 import BeautifulSoup, NavigableString, Tag


def main(path: str, start: int) -> None:
    print(f'The file path is: {path}')

    # Opening the TSV file
    with open(path, 'r', newline="", encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')

        # Iterating through rows
        for index, row in enumerate(reader):
            if index >= start:
                word = row[0]

                find_word(word)

                url = 'https://dic.b-amooz.com/de/dictionary/conjugation/v?verb=' + word
                response = requests.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')

                present_table = soup.select_one(
                    "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-body.px-0.pb-0 > div > div > div:nth-child(1) > div > div:nth-child(1) > table")
                past_table = soup.select_one(
                    "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-body.px-0.pb-0 > div > div > div:nth-child(1) > div > div:nth-child(3) > table")

                with open("template.html", "r") as template:
                    html_template = template.read()

                for i in (0, 2):
                    for j in range(1, 7):
                        table = present_table if i == 0 else past_table

                        result = table.select_one(f"table > tr:nth-child({j}) > td:nth-child(2) > span")

                        if result.attrs['class'][0] == 'normal':
                            result = f"<span style=\"color: #000\">{result.text.strip()}</span>"
                        elif result.attrs['class'][0] == 'irregular':
                            result = f"<span style=\"color: red\">{result.text.strip()}</span>"
                        else:
                            result = f"<span style=\"color: blue\">{result.text.strip()}</span>"

                        html_template = html_template.replace(f">present_{j}<" if i == 0 else f">past_{j}<",
                                                              f">{result}<")

                infinitive = soup.select_one(
                    "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(1) > span")
                third_state = soup.select_one(
                    "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(3) > span")
                past = soup.select_one(
                    "body > div.container.py-4.px-2.px-md-3.bg-white > div > div.card-header.px-0 > div.font-size-95.d-flex.flex-md-nowrap.flex-wrap.px-3.text-right.conjugation-meta-box > div:nth-child(2) > span")
                html_template = html_template.replace(">infinitive<", f'>{infinitive.text.strip()}<')
                html_template = html_template.replace(">past<", f'>{past.text.strip()}<')
                html_template = html_template.replace(">third_state<", f'>{third_state.text.strip()}<')

                # Write the data to a CSV file
                with open('output.csv', 'a', newline="", encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([html_template])


def find_word(word):
    # Retrieve and parse data from b-amooz.com
    dic_url = f"https://dic.b-amooz.com/de/dictionary/w?word={word}"
    response = requests.get(dic_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    result_list: list[dict]

    # Find container for word data
    container: list[Tag] = [child for child in soup.find(class_="container mt-2") if type(child) != NavigableString]

    # Divide list of rows by their role
    rows_list = []
    rows = []
    for div in container:
        if div.attrs['class'][0] == 'clearfix':
            rows_list.append(rows)
            rows = []
        else:
            rows.append(div)

    # Create List of data to be returned
    word_list = []
    for rows in rows_list:
        # Each iteration represent one data about one role of the word eg: name, verb, preposition, etc.

        word_data = {'role': None, 'deutsch': None, 'tags': None, 'meaning_data': [], 'notes': []}
        for index, row in enumerate(rows):
            # Each iteration except the first one represent one whole box for all the word meanings

            if index == 0:
                # The first box contains the details about the word itself

                # The german version of the word
                word_data['deutsch'] = row.select_one("div > div > div > h1").text.strip()

                # What is the role of the word in a sentence
                word_data['role'] = row.select_one("div > div > div > span").text.strip()[1:-1]

                # Finding and adding tags
                try:
                    word_data['tags'] = [item.text.strip() for item in
                                         row.find_all(class_="badge-pill badge-light ml-1")
                                         if item.text.strip()]
                except Exception as e:
                    print(f"word_data['tags']: {colorama.Fore.YELLOW + str(e) + colorama.Fore.RESET}")

                # Finding and adding extra data
                try:
                    word_data['extra'] = {key: val for key, val in tuple(
                        item.text.strip()[1:-1].split(":") for item
                        in row.select_one("div > div > div > div.text-muted")
                        if item.text.strip()[1:-1])}
                except Exception as e:
                    print(f"word_data['extra']: {colorama.Fore.YELLOW + str(e) + colorama.Fore.RESET}")

            else:
                # The rest of the boxes contains data about different meanings of the word

                # Finding the data of each meaning of the same role of the word
                word_data['meaning_data'].append({

                    # Adding the persian substitute and its secondary value to list of meanings of the role
                    "meanings": {'primary': row.select_one("div > div > div.row > div > h2 > strong").text.strip(),
                                 'secondary': row.select_one("div > div > div.row > div > h2 > small").text.strip()},

                    # Adding examples of one meaning of the role
                    "examples": get_examples(row),
                    "notes": get_notes(row),
                })

        word_list.append(word_data)

        pyperclip.copy(json.dumps(word_list))


def get_examples(row: Tag):
    def no_start_num(x: str) -> str:
        return re.sub(r'(^\d\.)|(^\d\. )', "", x).strip()

    example_pair_divs = row.find_all(class_='row p-0 mdc-typography--body2'
                                     ) + row.find_all(class_='row p-0 mdc-typography--body2 font-size-115')

    result = {}
    if example_pair_divs is not None:
        for example_pair_div in example_pair_divs:
            d = no_start_num(example_pair_div.select_one('div:nth-child(1)').text.strip())
            p = no_start_num(example_pair_div.select_one('div:nth-child(2)').text.strip())
            result[d] = p

    return result


def get_notes(row: Tag):
    result = []
    try:

        # Adding notes for each meaning
        notes = []
        for note_box in row.select("div.desc"):
            note = {note_box.select_one("h6").text.strip(): note_box.select_one('span').text.strip()}
            notes.append(note)

        if notes:
            result = notes
    except Exception as e:
        print(f"word_data['notes']: {colorama.Fore.YELLOW + str(e) + colorama.Fore.RESET}")

    return result


if __name__ == '__main__':
    file_path = sys.argv[1] if len(sys.argv[1]) > 1 else input(
        'Please write the file name or its path: ')
    start_row = int(sys.argv[2]) if len(sys.argv) > 2 else int(
        input('Please insert the starting row number: '))
    # main(path=file_path, start=start_row - 1)
    find_word('von')
