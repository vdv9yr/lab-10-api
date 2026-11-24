import logging

import html

from chalice import Chalice, NotFoundError, Response

from chalicelib.analyze import COLLECTION, DATABASE, analyze_book, connect

BUCKET = "public-vdv9yr"

app = Chalice(app_name="book-analyzer")

logging.getLogger().setLevel(logging.INFO)


@app.on_s3_event(bucket=BUCKET, events=["s3:ObjectCreated:*"], suffix=".txt")
def analyze_new_book(event):
    """Analyze a book when it is uploaded to BUCKET."""
    analyze_book(event.bucket, event.key)

# Lab 10: the API routes. They only read from MongoDB; none of them changes your data.

# Projection for get_book() (Step 2.4): all fields except runs and llm_analysis.at.
# They hold dates, and Chalice cannot turn a date into JSON.
BOOK_FIELDS = {"runs": 0, "llm_analysis.at": 0}


@app.route("/")
def index():
    """Return the number of books in the collection."""
    client = connect()
    try:
        count = client[DATABASE][COLLECTION].count_documents({})
    finally:
        client.close()  # close the connection to Atlas, also after an error
    return {"books": count}


@app.route("/books")
def list_books():
    """Return _id, title, and author of the books, sorted by title.

    The query parameter author, for example /books?author=Mark%20Twain, keeps only that author's books.
    """
    client = connect()
    try:
        params = app.current_request.query_params
        filter = {}

        if params and "author" in params:
            filter["author"] = params["author"]

        books = list(
            client[DATABASE][COLLECTION].find(
                filter, 
                {"title": 1, "author": 1}
            ).sort("title", 1)
        )
        return books
    finally:
        client.close()

@app.route("/books/{key}")
def get_book(key):
    """Return the document of one book, for example /books/pg11.txt; 404 if there is none."""
    #TODO Step 2.4: replace this line with your code (see the README)
    client = connect()
    try: 
        book = client[DATABASE][COLLECTION].find_one({"_id": key}, BOOK_FIELDS)
        
        if book is None:
            raise NotFoundError(f"No book with key {key}")
        
        return book
    finally:
        client.close()

@app.route("/page")
def page():
    """Return your book list as a web page for the browser; each title links to its document.

    It uses your list_books() function (Step 2.3), so it works once list_books() is done.
    /page?author=Mark%20Twain shows only that author's books, as /books does.
    """
    rows = []
    for book in list_books():
        key = html.escape(book["_id"])
        title = html.escape(book.get("title", "(no title)"))
        author = html.escape(book.get("author", "(unknown author)"))
        rows.append(f'<li><a href="books/{key}">{title}</a> by {author}</li>')
    body = "<!doctype html><title>My books</title><h1>My books</h1><ul>" + "".join(rows) + "</ul>"
    # Without this header, Chalice sends the text as JSON, and the browser shows the HTML code
    return Response(body=body, status_code=200, headers={"Content-Type": "text/html"})