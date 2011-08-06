from pypybuildbot import util

def test_symlink_force(tmpdir):
    one = tmpdir.join('one').ensure(file=True)
    two = tmpdir.join('two').ensure(file=True)
    latest = tmpdir.join('latest')
    util.symlink_force(str(one), str(latest))
    assert latest.readlink() == str(one)
    util.symlink_force(str(two), str(latest))
    assert latest.readlink() == str(two)
