def test_send_email():
    from bitbucket_hook.mail import send
    body = "This is a test to see if the bitbucket hook can send emails to the pypy-commit mailing list"
    send('antocuni <noreply@buildbot.pypy.org>',
         'pypy-commit@python.org',
         "this is a test",
         body,
         test=True)
