import asyncio
import csv
import datetime
import re
import sys

from bs4 import BeautifulSoup, Tag, NavigableString
from colorama import Fore as f
from httpx import AsyncClient

from Word import Word


async def auto(path: str, start: int) -> None:
    print(f'The file path is: {f.MAGENTA + path + f.RESET}')
    print(f'First word at row {f.MAGENTA + str(start + 1) + f.RESET}')

    # Create a list of rows
    rows = []
    # Create a list of rows
    columns = []

    # Create a set of words
    words = set()

    # Opening the TSV file
    with open(path, 'r', newline="", encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='\t')

        temp_word_set = set()  # Create a set to remove duplicate stripped words
        for index, row in enumerate(reader):  # Iterating through the rows of the file
            rows.append(row)

            if index == start - 1:
                columns = row

            if index >= start:
                # Store stripped word string in a temporary variable
                temp_word = re.sub(r'^(([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) )|^( *sich )', '',
                                   row[0]).strip().lower()

                if temp_word not in temp_word_set:
                    temp_word_set.add(temp_word)
                    words.add(row[0].lower())

    errors_non: dict = await create_final_result(words)

    # Create output file
    with open('output-a.txt', 'w', newline="", encoding='utf-8') as output:
        writer = csv.writer(output, delimiter='\t')

        # Write starting information on the new file
        writer.writerows(rows[0:start - 1])

        # Write column titles
        writer.writerow([
            'Text 1',  # ---------------------------------------------------------------- German word
            'Text 2',  # ---------------------------------------------------------------- Persian meaning
            'Text 3',  # ---------------------------------------------------------------- Artikel
            'Text 4',  # ---------------------------------------------------------------- No artikel
            'Text 5',  # ---------------------------------------------------------------- Word role in brackets
            'Text 6',  # ---------------------------------------------------------------- Plural form if exist
            'Text 7',  # ---------------------------------------------------------------- Conjugation

            'Category 1',  # ------------------------------------------------------------ Source of the word
            'Category 2',  # ------------------------------------------------------------ Word role

            'Statistics 1',  # ---------------------------------------------------------- German to persian data
            'Statistics 2',  # ---------------------------------------------------------- Persian to german data
            'Statistics 3',  # ---------------------------------------------------------- Der-Die-Das data
            'Statistics 4',  # ---------------------------------------------------------- Conjugation data
        ])

        # Write newly extracted data to the file
        for word_row in rows[start:]:
            word_row += [None for _ in range(len(columns) - len(word_row))]

            try:
                # Extract word data from dictionary
                data_list = errors_non.pop(word_row[0].lower())

            except KeyError as key_error:
                # Go for the next word if the key doesn't exist
                print("main: Key error: " + f.RED + str(key_error) + f.RESET)
                continue

            # Iterate through different roles of the word
            for data in data_list:
                data: Word

                # Initialising string for 'Text 2'
                text_2 = '<head><meta charset="UTF-8"><title></title></head><body>'
                text_2 += '<table style="width: 100%; border: 2px solid black;border-radius: 10px"><tbody>'
                for meaning in [meaning_data.meaning for meaning_data in data.meaning_data]:
                    text_2 += '<tr><td style="border-bottom: 1px solid black">'
                    text_2 += f'{meaning.primary}' \
                              f'{"<small> (" + meaning.secondary + ")</small>" if meaning.secondary else ""}'
                    text_2 += '</td></tr>'
                text_2 += '</tbody></table></body>'

                # Initialising string for 'Text 3'
                if data.role == 'اسم':
                    text_3 = re.match(r'^([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) ', data.deutsch).group(0).strip()
                else:
                    text_3 = ''

                # Initialising string for 'Text 4'
                text_4 = re.sub(r'^([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) ', '',
                                data.deutsch).strip() if data.role == 'اسم' else ''

                # Initialising string for 'Text 7'
                if data.role == 'فعل':
                    text_7 = data.conjugation_html
                else:
                    text_7 = ''

                writer.writerow(
                    [
                        data.deutsch,  # ------------------------------------------------ Text 1
                        text_2,  # ------------------------------------------------------ Text 2
                        text_3,  # ------------------------------------------------------ Text 3
                        text_4,  # ------------------------------------------------------ Text 4
                        f'[{data.role}]',  # -------------------------------------------- Text 5
                        data.plural if data.plural else '',  # -------------------------- Text 6
                        text_7,  # ------------------------------------------------------ Text 7

                        word_row[columns.index('Category 1')],  # ----------------------- Category 1 (Unchanged)
                        data.role,  # --------------------------------------------------- Category 2

                    ]

                    # Adding the 'Statistics' columns to the end
                    + [word_row[index] for index, val in enumerate(columns) if 'Statistics' in val]
                )


async def manual(word_set: set[str]) -> None:
    print(f'Manual extraction for {f.MAGENTA + str(len(word_set)) + f.RESET} words')

    words = {re.sub(r'^(([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) )|^( *sich )', '', word).strip().lower()
             for word in word_set}

    errors_non: dict = await create_final_result(words)

    # Create output file
    with open('output-m.txt', 'w', newline="", encoding='utf-8') as output:
        writer = csv.writer(output, delimiter='\t')

        # Write column titles
        writer.writerow([
            'Text 1',  # ---------------------------------------------------------------- German word
            'Text 2',  # ---------------------------------------------------------------- Persian meaning
            'Text 3',  # ---------------------------------------------------------------- Artikel
            'Text 4',  # ---------------------------------------------------------------- No artikel
            'Text 5',  # ---------------------------------------------------------------- Word role in brackets
            'Text 6',  # ---------------------------------------------------------------- Plural form if exist
            'Text 7',  # ---------------------------------------------------------------- Conjugation

            'Category 1',  # ------------------------------------------------------------ Source of the word
            'Category 2',  # ------------------------------------------------------------ Word role

            'Statistics 1',  # ---------------------------------------------------------- German to persian data
            'Statistics 2',  # ---------------------------------------------------------- Persian to german data
            'Statistics 3',  # ---------------------------------------------------------- Der-Die-Das data
            'Statistics 4',  # ---------------------------------------------------------- Conjugation data
        ])

        # Write newly extracted data to the file
        for word_str in errors_non.copy():
            data_list = errors_non.pop(word_str)

            # Iterate through different roles of the word
            for data in data_list:
                data: Word

                # Initialising string for 'Text 2'
                text_2 = '<head><meta charset="UTF-8"><title></title></head><body>'
                text_2 += '<table style="width: 100%; border: 2px solid black;border-radius: 10px"><tbody>'
                for meaning in [meaning_data.meaning for meaning_data in data.meaning_data]:
                    text_2 += '<tr><td style="border-bottom: 1px solid black">'
                    text_2 += f'{meaning.primary}' \
                              f'{"<small> (" + meaning.secondary + ")</small>" if meaning.secondary else ""}'
                    text_2 += '</td></tr>'
                text_2 += '</tbody></table></body>'

                # Initialising string for 'Text 3'
                if data.role == 'اسم':
                    text_3 = re.match(r'^([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) ', data.deutsch).group(0).strip()
                else:
                    text_3 = ''

                # Initialising string for 'Text 4'
                text_4 = re.sub(r'^([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) ', '',
                                data.deutsch).strip() if data.role == 'اسم' else ''

                # Initialising string for 'Text 7'
                if data.role == 'فعل':
                    text_7 = data.conjugation_html
                else:
                    text_7 = ''

                writer.writerow(
                    [
                        data.deutsch,  # ------------------------------------------------ Text 1
                        text_2,  # ------------------------------------------------------ Text 2
                        text_3,  # ------------------------------------------------------ Text 3
                        text_4,  # ------------------------------------------------------ Text 4
                        f'[{data.role}]',  # -------------------------------------------- Text 5
                        data.plural if data.plural else '',  # -------------------------- Text 6
                        text_7,  # ------------------------------------------------------ Text 7

                        None,  # -------------------------------------------------------- Category 1 (Unchanged)
                        data.role,  # --------------------------------------------------- Category 2

                    ]
                )


async def find_word(word: str, org_word=None) -> dict:
    """
    Takes a word as argument and extract its data from 'https://b-amooz.com'.
    :param org_word: Original word string to be returned as dictionary key. None for using word string as key.
    :param word: A word as string like 'sehen', 'auto', ...
    :return: A dict object with the given word string as key and extracted data or None or 404 as value.
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
    org_word = org_word if org_word else word
    word = re.sub(r'^(([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) )|( *sich )', '', word).strip().lower()

    try:
        # Retrieve and parse data from https://b-amooz.com
        url = f"https://dic.b-amooz.com/de/dictionary/w?word={word}"
        response = await AsyncClient().get(url, follow_redirects=True, timeout=60)
        soup = BeautifulSoup(response, 'html.parser')

        # Return 404 error if the string is not on the website as a german word
        if response.status_code == 404:
            return {org_word: 404}

        # Find container for word data
        container: list[Tag] = [child for child in soup.find(class_="container mt-2") if type(child) != NavigableString]

    except Exception as e:
        print(f"{f.MAGENTA + word + f.RESET}: {f.RED + str(e) + f.RESET}")
        return {org_word: None}

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

        word_data: Word = Word()
        for index, row in enumerate(rows):
            # Each iteration except the first one represent one whole box for all the word meanings

            if index == 0:  # The first box contains the details about the word itself

                # The german version of the word
                word_data.deutsch = row.select_one("div > div > div > h1").text.strip()

                # What is the role of the word in a sentence
                word_data.role = row.select_one("div > div > div > span").text.strip()[1:-1]

                # Adding verb conjugation
                if word_data.role == 'فعل':
                    word_data.conjugation_html = await verb_conjugation(
                        org_word, row.select_one('div > div > div > div.mx-n2.pt-2.mb-amp-3').find('a')['href'])

                # Finding and adding tags
                try:
                    word_data.tags = [item.text.strip() for item in
                                      row.find_all(class_="badge-pill badge-light ml-1")
                                      if item.text.strip()]
                except Exception as e:
                    print(f"{f.MAGENTA + word + f.RESET}: word_data['tags']: {f.YELLOW + str(e) + f.RESET}")

                # Finding and adding extra data
                try:
                    word_data.extra = {key.strip(): val.strip() for key, val in tuple(
                        item.text.strip()[1:-1].split(":") for item
                        in row.select_one("div > div > div > div.text-muted")
                        if item.text.strip()[1:-1])}

                    try:
                        word_data.plural = word_data.extra.pop('جمع')
                    except KeyError:
                        pass
                except TypeError:
                    pass

            else:  # The rest of the boxes contains data about different meanings of the word

                # Finding the data of each meaning of the same role of the word
                word_data.meaning_data.append(Word.MeaningData(
                    meaning=Word.MeaningData.Meaning(
                        primary=row.select_one("div > div > div.row > div > h2 > strong").text.strip(),
                        secondary=row.select_one("div > div > div.row > div > h2 > small").text.strip()),
                    examples=extract_examples(row),
                    notes=extract_notes(row)))

        word_list.append(word_data)

    # Create Word object and return it
    words = [word for word in word_list]
    return {org_word: words}


async def verb_conjugation(verb: str, url: str) -> str | None:
    """
    Get verb as string and extract its conjugation from https://b-amooz.com.
    :param url: The conjugation page url for the verb
    :param verb: word string just for logging
    :return: HTML text from 'conjugation_template.html' file in the same directory or None or '404'
    """

    try:
        # Retrieve and parse data from https://b-amooz.com
        response = await AsyncClient().get(url, follow_redirects=True, timeout=60)
        soup = BeautifulSoup(response, 'html.parser')

        # Return 404 error if the string is not on the website as a german verb
        if response.status_code == 404:
            return '404'

        # Find tables
        present_table = soup.select_one("div > div:nth-child(1) > div > div:nth-child(1) > table")
        past_table = soup.select_one("div > div:nth-child(1) > div > div:nth-child(3) > table")

    except Exception as e:
        print(f"{f.MAGENTA + verb + f.RESET}: {f.RED + str(e) + f.RESET}")
        return None

    # Read the template file
    with open("conjugation_template.html", "r", encoding='utf-8') as template:
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
        print(f"{f.MAGENTA + verb + f.RESET} verb: {f.RED + str(e) + f.RESET}")

    try:
        # Placing main data to html template
        html = html.replace(">past<", f">{info['گذشته']}<")
    except Exception as e:
        print(f"{f.MAGENTA + verb + f.RESET} verb: {f.RED + str(e) + f.RESET}")

    try:
        # Placing main data to html template
        html = html.replace(">third_state<", f">{info['حالت سوم فعل']}<")
    except Exception as e:
        print(f"{f.MAGENTA + verb + f.RESET} verb: {f.RED + str(e) + f.RESET}")

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

    corrected_dict = {}
    if errors_type == '404':
        for i, org_word in enumerate(words):
            word = re.sub(r'^([dD][eE][rR])|([dD][iI][eE])|([dD][aA][sS]) ', '', org_word).strip().lower()

            corrected_word = input(
                f'{i + 1}. Insert the correct form of {f.MAGENTA + word + f.RESET}. Type "c" to skip: ')
            if corrected_word != 'c' and corrected_word != 'C':
                corrected_dict.update({org_word: corrected_word})

        tasks = [asyncio.create_task(find_word(corrected_word, org_word=org_word), name=corrected_word)
                 for org_word, corrected_word in corrected_dict.items()]

    else:
        print(f'{f.YELLOW}Retry number {6 - retry} on failed attempts ...{f.RESET}')
        corrected_dict = {word: None for word in words}

        tasks = [asyncio.create_task(find_word(org_word), name=org_word)
                 for org_word in corrected_dict]

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


async def create_final_result(words: set[str]):
    # Create list of tasks to be executed asynchronously
    tasks = [asyncio.create_task(find_word(word), name=word) for word in words]

    print(f'Start scraping for {f.MAGENTA + str(len(tasks)) + f.RESET} words')

    # Record time
    start_time = datetime.datetime.now()

    # Wait for tasks to be completed
    word_results: dict = {key: val for result in await asyncio.gather(*tasks) for key, val in result.items()}

    # Calculating process duration
    duration = datetime.datetime.now() - start_time

    # Separate the results

    # errors_404: Mistyped words
    errors_404: set = set(key for key, val in word_results.items() if type(val) == int)
    # errors_net: Words with network error
    errors_net: set = set(key for key, val in word_results.items() if val is None)
    # errors_non: Successfully scraped words
    errors_non: dict = {key: val for key, val in word_results.items() if type(val) is list}

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

    return errors_non


if __name__ == '__main__':
    if sys.argv[1] != '-m':
        file_path = sys.argv[1] if len(sys.argv) > 1 else input('Please write the file name or its path: ')
        start_row = int(sys.argv[2]) if len(sys.argv) > 2 else int(input('Please insert the starting row number: '))
        asyncio.run(auto(path=file_path, start=start_row - 1))
    else:
        asyncio.run(manual(set(sys.argv[2:])))
