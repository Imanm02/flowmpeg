# UI recipe book

I use this page as a practical map for the local browser UI. Each recipe names
the input files, the Flowmpeg command to preview or run, the output to expect,
and the reason I would reach for it.

The UI runs the same `flowmpeg` command shown in each block. Open it with:

```console
flowmpeg ui
```

## Recipes

### Create demo media

Input: an empty folder such as `flowmpeg-demo`.

```console
flowmpeg demo-media flowmpeg-demo --overwrite
```

Output: small video, audio, image, subtitle, and image-sequence files in that
folder.

Why I use it: it gives me safe local files for testing the UI before I touch a
real project.
