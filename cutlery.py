import logging
import asyncio
from aiohttp import ClientSession, ClientResponseError
import re
import string
from selectolax.parser import HTMLParser
from gensim.parsing.preprocessing import remove_stopwords
import itertools
from collections import Counter
from statistics import mean
import nltk
import pandas as pd
from Color_Console import ctext
import os
from fake_useragent import UserAgent

# TODO: Fix Warning "DeprecationWarning: There is no current event loop"
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Show Full Results in Terminal During Processing
verbose = True

# Init Lists
titles_text = []
question_list = []
word_count_list = []
scraped_text_list = []
failed_pages_list = []

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO)
log = logging.getLogger(__name__)


async def fetch(session, url):
    try:
        async with session.get(url, timeout=15) as response:
            resp = await response.read()

            # Create Scraper
            tree = HTMLParser(resp)

            if tree is not None:
                junk = [
                    'style',
                    'script',
                    'xmp',
                    'iframe',
                    'noembed',
                    'noframes'
                ]
                tree.strip_tags(junk)

                title_tag_check = tree.css_first("title", strict=False)
                title_check = title_tag_check.text().strip()
                if title_check == "403 Forbidden":
                    failed_pages_list.append(url)
            return tree

    except ClientResponseError as e:
        log.warning(e.code)
        failed_pages_list.append(url)
    except asyncio.TimeoutError:
        log.warning("Timeout - {url}")
        failed_pages_list.append(url)
    except Exception as e:
        log.warning(e)
        failed_pages_list.append(url)
    return


async def fetch_async(URLS):
    tasks = []
    headers = {}
    random_viewer = UserAgent().random

    headers = {
        'Connection': 'keep-alive',
        'User-Agent': random_viewer
    }

    # Initialize Session and Start Tasks
    async with ClientSession(headers=headers) as session:
        for url in URLS:
            task = asyncio.create_task(fetch(session, url))
            tasks.append(task)

        # Await Response Outside the Loop
        responses = await asyncio.gather(*tasks)

    return responses


def shake_tree(tree):
    # Init Lists
    headings_list = []
    body_text = []

    # THIS IS A REALLY BAD TEMPORARY FIX FOR FAILED PAGES NEEDS FIX
    if tree is None:
        body_text_raw = ""
        title = "Failed"
        questions = []
        body_tokens = []
        word_count = 0

        return (
            title,
            body_text,
            questions,
            body_tokens,
            word_count,
        )

    # Remove Excess Whitespace from Scraped Page Content
    body_text_raw = " ".join(tree.body.text(separator=" ").split())

    # Attempt to Scrape Page Title
    title_tag = tree.css_first(
        "title", strict=False, default="Untitled"
    )

    # Catches the exception when the default flag is returned as it's a string
    try:
        title = title_tag.text().strip()
    except TypeError:
        title = title_tag
    # When there's still no title for some reason
    except AttributeError:
        title = "Untitled"

    # Scrape Tags H1-6 then Convert to Lowercase & Remove Excess Whitespace
    tags = ["h1", "h2", "h3", "h4", "h5", "h6"]
    for tag in tags:
        for node in tree.css(tag):
            headings_list.append(
                (" ".join((node.text().lower().strip()).split())))

    # Seperate Questions from Scraped Header Text & Convert to Lowercase
    questions_raw = [f.lower()
                     for f in headings_list if re.search(r".*[?=?]$", f)]

    # Remove Duplicate Questions
    questions = list(dict.fromkeys(questions_raw))

    # Remove Stopwords from Scraped Body Text
    body_text_cleaned = remove_stopwords(body_text_raw)

    # Remove Punctuation from Scraped Body Text
    punctuation_table = str.maketrans(dict.fromkeys(string.punctuation))
    body_text = body_text_cleaned.lower().translate(punctuation_table)

    # Tokenize body into a list and count the words
    body_tokens = body_text.split()
    word_count = len(body_tokens)

    return (
        title,
        body_text,
        questions,
        body_tokens,
        word_count
    )


def forest(trees):
    # Process Each Batch of HTML
    for tree in trees:
        (
            title,
            body_text,
            questions,
            body_tokens,
            word_count
        ) = shake_tree(tree)

        scraped_text_list.append(body_tokens)
        word_count_list.append(word_count)
        titles_text.append(title)
        question_list.append(questions)

    return (
        scraped_text_list,
        word_count_list, question_list,
        titles_text
    )


def garbage(text):
    """Remove Common Undesirable Results from Scraped Text"""
    junk_words = ["#"]  # Removes Duplicate Results Caused by Page Hooks

    # Check for garbage.txt File and Read into List if Available
    if os.path.isfile("garbage.txt"):
        with open("garbage.txt") as ignore_file:
            for line in ignore_file:
                junk_words.append(line.strip())
    else:
        log.warning(
            "garbage.txt not found - highly recommended to create it and populate it with a list of filtered keywords")

    # Check for Junk Words
    screened_text = [word for word in text if word.lower() not in junk_words]
    screened_words = [item for item in text if item not in screened_text]

    # Display Strings that Match Blacklist that will Be Ignored & Final List
    if verbose is True:
        ctext("\nIGNORED WORDS:\n", "yellow")
        if not screened_words:
            print("None to Ignore")
        else:
            print(" ".join(map(str, junk_words)))

    return screened_text


def get_grams(scraped_text, number_of_urls):
    """Get Ngrams from Text"""
    scraped_text_string = " ".join(scraped_text)
    scraped_text_tokens = scraped_text_string.split()

    bigram_freqs = nltk.FreqDist(nltk.bigrams(scraped_text_tokens))
    trigram_freqs = nltk.FreqDist(nltk.trigrams(scraped_text_tokens))
    bigrams = bigram_freqs.most_common()
    trigrams = trigram_freqs.most_common()

    # Unpack Bigrams into Dictionary
    bigram_dict = {" ".join(k): v for k, v in bigrams}

    # Unpack Trigrams into Dictionary
    trigram_dict = {" ".join(k): v for k, v in trigrams}

    # Create an Average Frequency Count of Each Ngram Based on Page Count
    bigram_dict.update(
        {n: bigram_dict[n] / number_of_urls for n in bigram_dict.keys()})
    trigram_dict.update(
        {n: trigram_dict[n] / number_of_urls for n in trigram_dict.keys()})

    # Round the Ngram Dictionaries to Whole Numbers
    bigram_dict = {k: round(v) for k, v in bigram_dict.items()}
    trigram_dict = {k: round(v) for k, v in trigram_dict.items()}

    # Minimum Frequency for Ngrams
    ngram_min_freq = 0

    # Remove Keys from Bigram Dictionary with Low Values
    for bigram in bigram_dict.copy():
        if bigram_dict[bigram] <= ngram_min_freq:
            del bigram_dict[bigram]

    # Remove Keys from Trigram Dictionary with Low Values
    for trigram in trigram_dict.copy():
        if trigram_dict[trigram] <= ngram_min_freq:
            del trigram_dict[trigram]

    if verbose is True:
        # Convert Ngram Dictionaries to Lists for Cleaner Display
        bigram_list = "\n".join(
            "{}: {}".format(k, v) for k, v in bigram_dict.items())
        trigram_list = "\n".join(
            "{}: {}".format(k, v) for k, v in trigram_dict.items())
    else:
        # Create Empty Lists if Not Needed to Save a Little Time
        bigram_list = []
        trigram_list = []

    return bigram_list, trigram_list, bigram_dict, trigram_dict


def query_engine(urls):
    # TODO: Remove this Manual Trigger
    csv_output = True

    # Show a Query has Started in Console/Logs
    log.info(f"Starting Scrape - Pages: {len(urls)}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    future = asyncio.ensure_future(fetch_async(urls))
    loop.run_until_complete(future)

    # Collect List of HTML Parser Objects from All Pages
    trees = future.result()

    (
        scraped_text_list,
        word_count_list,
        question_list,
        titles_text
    ) = forest(trees)

    # Display Page Titles When Possible
    if verbose is True:
        ctext("\nTITLES OF RANKED ARTICLES:\n", "yellow")
        print("\n".join(map(str, titles_text)))

    # Flatten Question List
    flat_questions = [item for sublist in question_list for item in sublist]

    # Found Questions List Displayed in Console
    if verbose is True:
        ctext("\nQUESTIONS FOUND:\n", "yellow")
        print(*flat_questions, sep="\n")

    # List of Word Counts are Prepared for Display and Shown
    if verbose is True:
        ctext("\nINDIVIDUAL PAGE WORD COUNTS:\n", "yellow")
        print(", ".join(map(str, word_count_list)))

    # Combine Scraped Text Lists to Parse for Data
    flat_list = list(itertools.chain(*scraped_text_list))

    # Remove Keywords with Less than 3 Characters
    flat_list_sifted = [i for i in flat_list if len(i) > 3]
    flat_list_sifted = garbage(flat_list_sifted)

    # Reduce Page Count to Account for Failed Pages
    number_of_urls = len(urls) - len(failed_pages_list)

    # Remove Failed URLS & Titles from the Matching Lists
    urls = [x for x in urls if x not in failed_pages_list]
    titles_text = [x for x in titles_text if x != "Failed"]

    # Get Bigrams and Trigrams from the Flat List of Scraped Text
    (
        bigram_list,
        trigram_list,
        bigram_dict,
        trigram_dict
    ) = get_grams(flat_list_sifted, len(urls))

    # Display any Higher Frequency Ngrams Found During Processing
    if verbose is True:
        ctext("\nHIGH FREQUENCY BIGRAMS FOUND:\n", "yellow")
        print(bigram_list)
        ctext("\nHIGH FREQUENCY TRIGRAMS FOUND\n", "yellow")
        print(trigram_list)

    # Count Top Keywords and their Total Frequency
    counter_of_flat_list = Counter(flat_list_sifted)
    count_freqs = counter_of_flat_list.most_common(100)

    # Covert from Tuple to Dict for Easier Handling
    average_freqs = dict(count_freqs)

    # Calculate Average Keyword Frequency & Round Results
    average_freqs.update(
        {n: average_freqs[n] / number_of_urls for n in average_freqs.keys()}
    )
    average_freqs = {k: round(v) for k, v in average_freqs.items()}

    # Display Top Keywords Found Along with their Total Averages Across Pages
    if verbose is True:
        ctext("\nTOP KEYWORDS FREQUENCY AVERAGE:\n", "yellow")
        print(
            "\n".join("{}: {}".format(k, v) for k, v in average_freqs.items())
        )

    # Remove Zero Values from Word Count List
    word_count_list = [x for x in word_count_list if x != 0]

    # Average Out a Word Count from the Pages
    average_word_count = round(mean(word_count_list))
    if verbose is True:
        ctext("\nAVERAGE WORD COUNT:\n", "yellow")
        print(f"{average_word_count} from a total of {number_of_urls} Pages")
        ctext("\nFailed Pages:", "yellow")
        print(len(failed_pages_list), "\n")

    # Covert Word Count to String and Add Average Flag for CSV Export
    word_count_list.append("Average: " + str(average_word_count))

    # Create Dataframes & Join them Seperately to Avoid Cutoff
    exportable = pd.concat(
        [
            pd.DataFrame(zip(
                titles_text, urls), columns=["Titles", "URLS"]),
            pd.DataFrame(list(
                word_count_list), columns=["Word_Count"]),
            pd.DataFrame(list(
                flat_questions), columns=["Questions"]),
            pd.DataFrame(list(
                average_freqs.items()), columns=["Keyword", "Frequency"]),
            pd.DataFrame(list(
                bigram_dict.items()), columns=["Bigrams", "Bi_Freq"]),
            pd.DataFrame(list(
                trigram_dict.items()), columns=["Trigrams", "Tri_Freq"]),
        ],
        axis=1,
    )

    if csv_output == True:
        csv_export = exportable.to_csv(index=False)
        with open("output.csv", "w") as output_file:
            output_file.write(csv_export)

        log.info("Results saved to 'output.csv'")
    else:
        return "TODO: Add Alternative Exports"


def main():
    with open("input.txt") as file:
        urls = [line.rstrip() for line in file]

    if len(urls) < 2:
        log.error(
            "Not Enough URLs - minimum 2 are required to be added to input.txt")
        exit()

    query_engine(urls)


if __name__ == "__main__":
    main()
