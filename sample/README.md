# Ricty Diminished with icons

プログラミング用フォント「[Ricty Diminished](http://www.rs.tus.ac.jp/yyusa/ricty_diminished.html)」にアイコンフォントを合成したものを用意しました。


## 環境

- macOS Sierra (Version 10.12.3)
- Python 2.7.13
- libfontforge 20170104

## 手順

```
$ curl http://www.rs.tus.ac.jp/yyusa/ricty_diminished/ricty_diminished-4.1.0.tar.gz | tar xvz
$ fontforge -script mergefonts.py --all -o sample --suffix=with-icons -- RictyDiminished-Regular.ttf RictyDiminished-Bold.ttf RictyDiminishedDiscord-Regular.ttf RictyDiminishedDiscord-Bold.ttf
```

## ライセンス

`sample/`ディレクトリ以下に含まれるフォントファイル( `*.ttf` )は [Ricty Diminished](http://www.rs.tus.ac.jp/yyusa/ricty_diminished.html)と同様 [SIL Open Font License (OFL) Version 1.1](http://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=ofl) に従うものとします。