import asyncio
import csv
import datetime
import re
import sys

import pyperclip
from bs4 import BeautifulSoup, Tag, NavigableString
from colorama import Fore as f
from httpx import AsyncClient

from Word import Word


async def main(path: str, start: int) -> None:
    print(f'The file path is: {f.MAGENTA + path + f.RESET}')
    print(f'First word at row {f.MAGENTA + str(start + 1) + f.RESET}')

    # Create list of words and removing duplicates
    words = set()

    # Opening the TSV file
    with open(path, 'r', newline="", encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='\t')

        for index, row in enumerate(reader):  # Iterating through the rows of the file
            if index >= start:
                words.add(row[0].lower())

    # Create list of tasks to be executed asynchronously
    tasks = [asyncio.create_task(find_word(word), name=word) for word in words]

    print(f'Start scraping for {f.MAGENTA + str(len(tasks)) + f.RESET} words')

    # Record time
    start_time = datetime.datetime.now()

    # Wait for tasks to be completed
    results: dict = {key: val for result in await asyncio.gather(*tasks) for key, val in result.items()}

    # Calculating process duration
    duration = datetime.datetime.now() - start_time

    # Separate the results

    # errors_404: Mistyped words
    errors_404: set = set(key for key, val in results.items() if type(val) == int)
    # errors_net: Words with network error
    errors_net: set = set(key for key, val in results.items() if val is None)
    # errors_non: Successfully scraped words
    errors_non: dict = {key: val for key, val in results.items() if type(val) is list}

    # Print summary
    print(f.GREEN + str(len(errors_non)) + f.RESET + ' data extracted in ' + f.GREEN + str(
        duration.seconds) + f.RESET + ' seconds.')
    print(f"Couldn't find {f.RED + str(len(errors_404)) + f.RESET} words:")
    for error in errors_404:
        print(error)
    print(f'Network error on {f.RED + str(len(errors_net)) + f.RESET} words:')
    for error in errors_net:
        print(error)

    # Retry words with network error if exist
    if errors_net:
        confirmation = input("Do you want to retry the words with network problem? (y/n) ")
        while True:
            if confirmation in ('y', "Y"):
                print(f.YELLOW + 'Retrying failed attempts ...' + f.RESET)
                corrected_dicts = await correct_errors(errors_net, errors_type='net')
                errors_non.update(corrected_dicts['errors_non'])
                errors_404.update(corrected_dicts['errors_404'])
                errors_net.update(corrected_dicts['errors_net'])
                break

            elif confirmation in ('n', "N"):
                # TBC
                break

            else:
                confirmation = input("I didn't understand that. "
                                     + "Do you want to retry the words with network problem? (Type 'y' or 'n') ")

    # Asking user to correct mistyped words
    if errors_404:
        print(f.YELLOW + 'Starting words correction' + f.RESET)
        corrected_dicts = await correct_errors(errors_404)
        errors_non.update(corrected_dicts['errors_non'])
        errors_net.update(corrected_dicts['errors_net'])

    # Create list of verbs
    verbs = {word_Str: word for word_Str, words in errors_non.items() for word in words if word.role == 'فعل'}

    # Create task for verb conjugation scraping
    tasks = [asyncio.create_task(verb_conjugation(word), name=word_Str) for word_Str, word in verbs.items()]

    # Verb conjugation scraping
    results: list[str] = [result for result in await asyncio.gather(*tasks)]

    # TBC


async def find_word(word: str) -> dict:
    """
    Takes a word as argument and extract its data from 'https://b-amooz.com'
    :param word: A string like 'sehen', 'auto', ...
    :return: A dict object with the stripped word as key and extracted data or None or 404 as value
    """

    def extract_examples(example_row: Tag):
        def no_start_num(x: str) -> str:
            return re.sub(r'(^\d\.)|(^\d\. )', "", x).strip()

        example_pair_divs = example_row.find_all(class_='row p-0 mdc-typography--body2'
                                                 ) + example_row.find_all(
            class_='row p-0 mdc-typography--body2 font-size-115')

        result = {}
        if example_pair_divs is not None:
            for example_pair_div in example_pair_divs:
                d = no_start_num(example_pair_div.select_one('div:nth-child(1)').text.strip())
                p = no_start_num(example_pair_div.select_one('div:nth-child(2)').text.strip())
                result[d] = p

        return result

    def extract_notes(note_row: Tag):
        result = []
        try:

            # Adding notes for each meaning
            notes = []
            for note_box in note_row.select("div.desc"):
                note = {
                    note_box.select_one("h6").text.strip(): [text.text.strip() for text in note_box.select_one('span')]}
                notes.append(note)

            if notes:
                result = notes
        except Exception as error:
            print(f"word_data['notes']: {f.YELLOW + str(error) + f.RESET}")

        return result

    # Cut the article from the beginning of the string
    word = re.sub(r'^[dD][iIeEaA][rReEsS] ', '', word).strip().lower()

    try:
        # Retrieve and parse data from https://b-amooz.com
        url = f"https://dic.b-amooz.com/de/dictionary/w?word={word}"
        response = await AsyncClient().get(url, follow_redirects=True, timeout=60)
        soup = BeautifulSoup(response, 'html.parser')

        # Return 404 error if the string is not on the website as a german word
        if response.status_code == 404:
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

                # Adding link for verb conjugation
                if word_data['role'] == 'فعل':
                    word_data['conjugation_url'] = \
                        row.select_one('div > div > div > div.mx-n2.pt-2.mb-amp-3').find('a')['href']

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
                    "examples": extract_examples(row),
                    "notes": extract_notes(row),
                })
        word_list.append(word_data)

    # Create Word object and return it
    words = [Word(**word) for word in word_list]
    return {word: words}


async def verb_conjugation(verb: Word) -> str | None:
    """
    Get verb as string and extract its conjugation from https://b-amooz.com.
    :param verb: verb text
    :return: HTML text from 'template.html' file in the same directory or None or '404'
    """

    try:
        # Retrieve and parse data from https://b-amooz.com
        url = verb.conjugation_url
        response = await AsyncClient().get(url, follow_redirects=True, timeout=60)
        soup = BeautifulSoup(response, 'html.parser')

        # Return 404 error if the string is not on the website as a german verb
        if response.status_code == 404:
            return '404'

        # Find tables
        present_table = soup.select_one("div > div:nth-child(1) > div > div:nth-child(1) > table")
        past_table = soup.select_one("div > div:nth-child(1) > div > div:nth-child(3) > table")

    except Exception as e:
        print(f"{f.MAGENTA + verb.deutsch + f.RESET}: {f.RED + str(e) + f.RESET}")
        return None

    # Read the template file
    with open("template.html", "r") as template:
        html = template.read()

    # Two iteration for two important tables in the template
    for i in (0, 2):

        for j in range(1, 7):
            table = present_table if i == 0 else past_table

            result = table.select_one(f"table > tr:nth-child({j}) > td:nth-child(2) > span")

            # Check for verb irregularity
            if result.attrs['class'][0] == 'normal':
                result = f"<span style=\"color: #000\">{result.text.strip()}</span>"
            elif result.attrs['class'][0] == 'irregular':
                result = f"<span style=\"color: red\">{result.text.strip()}</span>"
            else:
                result = f"<span style=\"color: blue\">{result.text.strip()}</span>"

            # Place data to template
            html = html.replace(f"[present_{j}]" if i == 0 else f"[past_{j}]", f"{result}")

    # Extracting main info about the verb
    info_div = soup.select_one('body > div.container > div > div.card-header > div.font-size-95')
    info = {}
    for i in range(len(info_div)):
        pair = info_div.select_one(f'div:nth-child({i})')
        if pair:
            info[pair.find('b').text.replace(":", "").strip()] = pair.find('span').text.strip()

    try:
        # Placing main data to html template
        html = html.replace(">infinitive<", f">{info['مصدر']}<")
    except Exception as e:
        print(f"{f.MAGENTA + verb.deutsch + f.RESET} verb: {f.RED + str(e) + f.RESET}")

    try:
        # Placing main data to html template
        html = html.replace(">past<", f">{info['گذشته']}<")
    except Exception as e:
        print(f"{f.MAGENTA + verb.deutsch + f.RESET} verb: {f.RED + str(e) + f.RESET}")

    try:
        # Placing main data to html template
        html = html.replace(">third_state<", f">{info['حالت سوم فعل']}<")
    except Exception as e:
        print(f"{f.MAGENTA + verb.deutsch + f.RESET} verb: {f.RED + str(e) + f.RESET}")

    # Return result
    return html


async def correct_errors(words: set[str], errors_type: str = '404', retry: int = 5) -> dict:
    """
    Keeps asking user to correct the 404_error words till there's no error
    :param retry: Number of retry allowed. Default is 5
    :param words: List of words
    :param errors_type: Type of the error of the words list. Could be '404' or 'net'. Default is '404'
    :return: extracted words data as dictionary
    """

    corrected_words = []
    if errors_type == '404':
        for i, word in enumerate(words):
            corrected_word = input(
                f'{i + 1}. Insert the correct form of {f.MAGENTA + word + f.RESET}. Type "c" to skip: ')
            if corrected_word != 'c' and corrected_word != 'C':
                corrected_words.append(corrected_word)
    else:
        print(f'{f.YELLOW}Retry number {6 - retry} on failed attempts ...{f.RESET}')
        corrected_words = words

    tasks = [asyncio.create_task(find_word(corrected_word), name=corrected_word) for corrected_word in corrected_words]

    # Store starting time
    start_time = datetime.datetime.now()

    # Wait for tasks to be completed
    temp = await asyncio.gather(*tasks)
    results: dict = {key: val for result in temp for key, val in result.items()}

    # Calculating process duration
    duration = datetime.datetime.now() - start_time
    print(f.GREEN + str(len(results)) + f.RESET + ' data extracted in ' + f.GREEN + str(
        duration.seconds) + f.RESET + ' seconds.')

    # Separate the results
    errors_404: set = set(key for key, val in results.items() if type(val) == int)
    errors_net: set = set(key for key, val in results.items() if val is None)
    errors_non: dict = {key: val for key, val in results.items() if type(val) is list}

    if errors_net and errors_type == 'net':
        if retry <= 0:
            print(f.RED + "Maximum allowed retry reached." + f.RESET)
            return {'errors_non': errors_non, 'errors_net': errors_net, 'errors_404': errors_404}
        else:
            corrected_dicts = await correct_errors(errors_net, errors_type='net', retry=retry - 1)
            errors_non.update(corrected_dicts['errors_non'])
            errors_404.update(corrected_dicts['errors_404'])
            errors_net = corrected_dicts['errors_net']

    if errors_404 and errors_type == '404':
        print(f.YELLOW + f'Starting words correction for {f.RED + str(len(errors_404)) + f.YELLOW} words' + f.RESET)
        corrected_dicts = await correct_errors(errors_404)
        errors_non.update(corrected_dicts['errors_non'])
        errors_net.update(corrected_dicts['errors_net'])
        errors_404 = corrected_dicts['errors_404']

    return {'errors_non': errors_non, 'errors_net': errors_net, 'errors_404': errors_404}


if __name__ == '__main__':
    file_path = sys.argv[1] if len(sys.argv) > 1 else input('Please write the file name or its path: ')
    start_row = int(sys.argv[2]) if len(sys.argv) > 2 else int(input('Please insert the starting row number: '))
    asyncio.run(main(path=file_path, start=start_row - 1))
