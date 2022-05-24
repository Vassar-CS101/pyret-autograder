# CMPU 101 Pyret Autograding

To prepare the autograder for use with Gradescope:

1. Create/find the assignment subdirectory in the [`pyret-assignments`
repository](https://github.com/Vassar-CS101/pyret-assignments).

2. Place wheats, chaffs, tests, and stencil files in their respective
directories.

3. Update `points.json` to match the wheats, chaffs, and tests.

4. Zip the contents of the branch and upload to Gradescope.


## Archiving a semester

At the end of each semester, make an annotated tag, e.g.,

```
git tag -a 2021b -m "Spring 2021"
git push --tags
```

In the tag names, `a` is Spring and `b` is Fall so they sort correctly.

This allows the autograders used in previous semesters to be easily downloaded 
from GitHub as zip files.
