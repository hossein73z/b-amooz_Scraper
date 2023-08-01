import asyncio
import csv
import datetime
import re
import sys

from bs4 import BeautifulSoup, Tag, NavigableString
from colorama import Fore as f
from httpx import AsyncClient

from Word import Word


async def main(path: str, start: int) -> None:
    print(f'The file path is: {f.MAGENTA + path + f.RESET}')
    print(f'First word at row {f.MAGENTA + str(start + 1) + f.RESET}')

    # Opening the TSV file
    with open(path, 'r', newline="", encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='\t')

        # Create list of tasks to be executed asynchronously
        tasks = []
        for index, row in enumerate(reader):  # Iterating through the rows of the file
            if index >= start:
                word = row[0]

                # Call 'find_word()' function in each task
                tasks.append(asyncio.create_task(find_word(word), name=word))

        print(f'Starting extraction on {f.MAGENTA + str(len(tasks)) + f.RESET} words')

        # Record time
        start_time = datetime.datetime.now()

        # Wait for tasks to be completed
        temp = await asyncio.gather(*tasks)
        results: dict = {key: val for result in temp for key, val in result.items()}

        # Calculating process duration
        duration = datetime.datetime.now() - start_time

        # Separate the results
        error_404_dict = {key: val for key, val in results.items() if type(val) == int}
        error_net_dict = {key: val for key, val in results.items() if val is None}
        error_non_dict = {key: val for key, val in results.items() if type(val) is list}

        # Print summary
        print(f.GREEN + str(len(error_non_dict)) + f.RESET + ' data extracted in ' + f.GREEN + str(
            duration.seconds) + f.RESET + ' seconds.')
        print(f"Couldn't find {f.RED + str(len(error_404_dict)) + f.RESET} words:")
        for error in error_404_dict:
            print(error)
        print(f'Network error on {f.RED + str(len(error_net_dict)) + f.RESET} words:')
        for error in error_net_dict:
            print(error)


async def find_word(word) -> dict:
    """
    Takes a word as argument and extract its data from 'https://b-amooz.com'
    :param word: A string like 'sehen', 'auto', ...
    :return: A dict object with the stripped word as key and extracted data or None or 404 as value
    """

    # Cut the article from the beginning of the string
    word = re.sub(r'^[dD][iIeEaA][rReEsS] ', '', word).strip()

    try:
        # Retrieve and parse data from https://b-amooz.com
        url = f"https://dic.b-amooz.com/de/dictionary/w?word={word}"
        response = await AsyncClient().get(url, follow_redirects=True, timeout=60)
        soup = BeautifulSoup(response, 'html.parser')

        # Return 404 error if the string is not on the website as a german word
        if response.status_code == 404:
            # print(f"{f.MAGENTA + word + f.RESET}: {f.RED + 'Error 404' + f.RESET}")
            return {word: 404}

        # Find container for word data
        container: list[Tag] = [child for child in soup.find(class_="container mt-2") if type(child) != NavigableString]

    except Exception as e:
        print(f"{f.MAGENTA + word + f.RESET}: {f.RED + str(e) + f.RESET}")
        return {word: None}

    # Divide list of rows by their role
    rows_list = []
    rows = []
    for div in container:
        if div.attrs['class'][0] == 'clearfix':
            rows_list.append(rows)
            rows = []
        else:
            rows.append(div)

    # Create List of word objects to be returned
    word_list = []
    for rows in rows_list:  # Each iteration represent data about one role of the word eg: name, verb, preposition, etc.

        word_data = {'role': None, 'deutsch': None, 'tags': None, 'meaning_data': []}
        for index, row in enumerate(rows):
            # Each iteration except the first one represent one whole box for all the word meanings

            if index == 0:  # The first box contains the details about the word itself

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
                    print(f"{f.MAGENTA + word + f.RESET}: word_data['tags']: {f.YELLOW + str(e) + f.RESET}")

                # Finding and adding extra data
                try:
                    word_data['extra'] = {key: val for key, val in tuple(
                        item.text.strip()[1:-1].split(":") for item
                        in row.select_one("div > div > div > div.text-muted")
                        if item.text.strip()[1:-1])}
                except TypeError:
                    pass

            else:  # The rest of the boxes contains data about different meanings of the word

                # Finding the data of each meaning of the same role of the word
                word_data['meaning_data'].append({

                    # Adding the persian substitute and its secondary value to list of meanings of the role
                    "meaning": {'primary': row.select_one("div > div > div.row > div > h2 > strong").text.strip(),
                                'secondary': row.select_one("div > div > div.row > div > h2 > small").text.strip()},

                    # Adding examples of one meaning of the role
                    "examples": get_examples(row),
                    "notes": get_notes(row),
                })
        word_list.append(word_data)

    # Create Word object and return it
    words = [Word(**word) for word in word_list]
    return {word: words}


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
            note = {note_box.select_one("h6").text.strip(): [text.text.strip() for text in note_box.select_one('span')]}
            notes.append(note)

        if notes:
            result = notes
    except Exception as e:
        print(f"word_data['notes']: {f.YELLOW + str(e) + f.RESET}")

    return result


if __name__ == '__main__':
    file_path = sys.argv[1] if len(sys.argv) > 1 else input('Please write the file name or its path: ')
    start_row = int(sys.argv[2]) if len(sys.argv) > 2 else int(input('Please insert the starting row number: '))
    asyncio.run(main(path=file_path, start=start_row - 1))
