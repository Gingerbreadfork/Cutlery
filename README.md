# Cutlery
Python Script for Copywriters to Gather Data from Competing Content and Find Keyword Overlap

## Usage
1. Clone this repo `git clone https://github.com/Gingerbreadfork/Cutlery`  
2. `pip install -r requirements.txt` to install dependencies (ideally in a virtualenv)  
3. Add URLs to process (one per line) to `input.txt`  
4. Run script `python3 cutlery.py`
5. Open `output.csv` in your CSV reader of choice to view the results

## Notes
* You can add or remove filtered keywords simply by adding them to `garbage.txt`
* If you are doing multiple runs just rename `output.csv` to something else each time
* You will get better results when comparing smaller amounts of higher quality content
* This is only tested on Linux, generally works without any hassles on popular distros
* Likely works just fine too on Windows & MacOS, it just hasn't been checked
* Long tail keyword results (trigrams and bigrams) don't account for loss of stop words (e.g if, than, to, so) so may occasionally present weirdly but it's usually pretty obvious what is missing when it happens.
* Don't rely on tools like this to drive your SEO efforts, just use them to help you create better content by finding common topics, questions, and keywords to inspire your own content from other content you already know is performing well.
* Contributions are welcome!

## TODO:
This is a refresh of some old code used to assist with outline prep as part of a custom workflow, there's some weird work arounds and some pretty dusty code around the place.

## Find this Useful?

Drop a ⭐ and give me a yell on Twitter [@gingerbreadfork](https://twitter.com/gingerbreadfork) 🤘
