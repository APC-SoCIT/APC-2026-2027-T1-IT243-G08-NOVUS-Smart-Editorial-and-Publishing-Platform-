"""Gunicorn settings, read automatically from the directory it starts in.
 
The default worker timeout is 30 seconds, the same as the assessment's limit
(NFR-02). A submission that used its full allowance would have its worker
killed mid-request, leaving the article stuck awaiting evaluation. The
worker's limit sits above the assessment's, so the assessment always times
out first and the article goes to manual review instead.
"""
timeout = 60
