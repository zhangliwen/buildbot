from pypybuildbot import util

def test_symlink_force(tmpdir):
    one = tmpdir.join('one').ensure(file=True)
    two = tmpdir.join('two').ensure(file=True)
    latest = tmpdir.join('latest')
    util.symlink_force(str(one), str(latest))
    assert latest.readlink() == str(one)
    util.symlink_force(str(two), str(latest))
    assert latest.readlink() == str(two)

def test_clean_old_files(tmpdir):
    one = tmpdir.join('one/tmp.txt').ensure(file=True)
    two = tmpdir.join('one/two/tmp.txt').ensure(file=True)
    two.setmtime(two.mtime() - 90*24*60*60)
    util.clean_old_files(one.dirname, 40)
    assert one.exists()
    assert not two.exists()
    assert two.dirpath().exists()
    # empty directory only removed on second run
    util.clean_old_files(one.dirname, 40)
    assert not two.dirpath().exists()
    
    
