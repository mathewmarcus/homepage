from argparse import ArgumentParser, FileType
from sys import stdout
from bs4 import BeautifulSoup
from bs4.element import Tag
from os.path import basename
import subprocess

parser = ArgumentParser(description='convert supplied markdown file to html and write it to new html file based on <template>')
parser.add_argument('markdown_input')
parser.add_argument('--output', '-o', default=stdout, type=FileType('w'))
parser.add_argument('--html_template', '-t', default='./templates/blog_post.html', type=FileType('r'))


def main():
    args = parser.parse_args()

    completed_process = subprocess.run(['showdown', 'makehtml', '-i', args.markdown_input], stdout=subprocess.PIPE, encoding='utf-8')
    completed_process.check_returncode()
    md_html = completed_process.stdout

    md_html = BeautifulSoup(md_html, 'html.parser')

    for link in md_html.find_all('a'):
        link['target'] = '_blank'

    main_tag = Tag(name='main')
    main_tag['class'] = 'container'
    main_tag.append('\n')

    # this is a somewhat obnoxious workaround to md_html.wrap(Tag(name='main'))
    # because that returns an exception which says you can't wrap an entire bs4.BeautifulSoup object
    for child in md_html.children:
        main_tag.append(child)
    main_tag.append('\n')

    template_html = BeautifulSoup(args.html_template, 'html.parser')

    try:
        template_html.body.main.replace_with(main_tag)
    except AttributeError:
        template_html.body.footer.insert_before(main_tag)

    disqus_script = template_html.body.footer.script
    disqus_script.string = disqus_script.string.replace('PAGE_IDENTIFIER',
                                                        '\'' + basename(args.markdown_input).split('.')[0] + '\'')

    args.output.write(str(template_html))


if __name__ == '__main__':
    main()
