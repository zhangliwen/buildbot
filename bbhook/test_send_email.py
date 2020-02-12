def test_send_email():
    from bbhook.mail import send
    body = "This is a test to see if the mercurial hook can send emails to the pypy-commit mailing list"
    send('antocuni <noreply@buildbot.pypy.org>',
         'pypy-commit@python.org',
         "this is a test",
         body,
         test=True)
