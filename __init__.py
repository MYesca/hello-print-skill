import html
import io
import json 
from itertools import zip_longest
from urllib.request import Request, urlopen
from mycroft import MycroftSkill, intent_file_handler
from mycroft.client.enclosure.emilia import PrinterCommand
from mycroft.util.log import LOG
from time import sleep
import smtplib
from email.message import EmailMessage

ul = b'\xC9'.decode('CP850')
um = b'\xCB'.decode('CP850')
ur = b'\xBB'.decode('CP850')
dl = b'\xC8'.decode('CP850')
dm = b'\xCA'.decode('CP850')
dr = b'\xBC'.decode('CP850')
ml = b'\xCC'.decode('CP850')
mm = b'\xCE'.decode('CP850')
mr = b'\xB9'.decode('CP850')
ho = b'\xCD'.decode('CP850')
ve = b'\xBA'.decode('CP850')
blk = b'\xDB'.decode('CP850')
leton = b'\x1B\x47'.decode('CP850')
letoff = b'\x1B\x48'.decode('CP850')
supon = b'\x1B\x53\x00'.decode('CP850')
supoff = b'\x1B\x54'.decode('CP850')
expon = b'\x1B\x57\x01'.decode('CP850')
expoff = b'\x1B\x57\x00'.decode('CP850')
conon = b'\x0F'.decode('CP850')
conoff = b'\x12'.decode('CP850')


class HelloPrint(MycroftSkill):


    def __init__(self):
        MycroftSkill.__init__(self)
    

    def getData(self):
        req = Request('https://www.xwordinfo.com/JSON/Data.aspx?date=random')
        req.add_header('Referer', 'https://www.xwordinfo.com/JSON/Sample1')
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data


    def getMatrix(self, rows, cols, cellHeight, cellWidth):

        matrix = []

        for y in range(1, rows+1):
            if y == 1:
                row = [ul]
                for x in range(1, cols+1):
                    for j in range(cellWidth):
                        row.append(ho)
                    row.append(um if x < cols else ur)
                matrix.append(row)

            for i in range(cellHeight):
                row = [ve]
                for x in range(1, cols+1):
                    for j in range(cellWidth):
                        row.append(' ')
                    row.append(ve)
                matrix.append(row)

            if y < rows:
                row = [ml]
                for x in range(1, cols+1):
                    for j in range(cellWidth):
                        row.append(ho)
                    row.append(mm if x < cols else mr)
                matrix.append(row)
            else:
                row = [dl]
                for x in range(1, cols+1):
                    for j in range(cellWidth):
                        row.append(ho)
                    row.append(dm if x < cols else dr)
                matrix.append(row)

        return matrix


    def fillMatrix(self, matrix, data, cellHeight, cellWidth, withAnswers=False):
        n = 0
        for row in range(data['size']['rows']):
            for col in range(data['size']['cols']):
                num = data['gridnums'][n]
                val = data['grid'][n]
                y = row * (cellHeight+1) + 1
                x = col * (cellWidth+1) + 1
                if val == '.':
                    for i in range(cellHeight):
                        for j in range(cellWidth):
                            matrix[y+i][x+j] = blk
                else:
                    digits = '  ' if num == 0 else format(num, '2')
                    matrix[y][x] = digits[0] #supon + digits[0]
                    matrix[y][x+1] = digits[1] #+ supoff
                    if withAnswers:
                        for p in range(len(val)):
                            matrix[y + 1 + p//cellWidth][x + p%cellWidth] = val[p]
                n += 1
        return matrix


    def getXwordJob(self, data):
        title = data['title']
        author = data['author']
        copy = data['copyright']

        matrix = self.getMatrix(data['size']['rows'], data['size']['cols'], 2, 4)
        matrix = self.fillMatrix(matrix, data, 2, 4, False)

        output = io.StringIO()

        print(f'{expon}{title}{expoff}', file=output)
        print(f'By {author}', file=output)
        print(' ', file=output)
        print(conon, file=output)
        for row in matrix:
            line = ''
            for cara in row:
                line += cara
            print(line, file=output)
        print(f'@ {copy}', file=output)
        print(f'{conoff}', file=output)

        cluesAcross = []
        for raw in data['clues']['across']:
            line = html.unescape(raw)
            cluesAcross.append(line[:36] if len(line) > 36 else line)
            if len(line) > 36:
                cluesAcross.append(f'   {line[36:]}')

        cluesDown = []
        for raw in data['clues']['down']:
            line = html.unescape(raw)
            cluesDown.append(line[:36] if len(line) > 36 else line)
            if len(line) > 36:
                cluesDown.append(f'   {line[36:]}')

        print(f'{leton}ACROSS:'.ljust(40) + 'DOWN:', file=output)
        for across, down in zip_longest(cluesAcross, cluesDown, fillvalue=' '):
            print(across.ljust(38) + down, file=output)

        print(f'{letoff}', file=output)

        xword = output.getvalue()
        output.close()

        return xword


    def getXwordMail(self, data):
        title = data['title']
        author = data['author']
        copy = data['copyright']

        matrix = self.getMatrix(data['size']['rows'], data['size']['cols'], 3, 3)
        matrix = self.fillMatrix(matrix, data, 3, 3, True)

        output = io.StringIO()

        print(f'<p><h1>{title}</h1></p>', file=output)
        print(f'<p><i>By {author}</i></p>', file=output)
        print('<p><pre>', file=output)
        for row in matrix:
            line = ''
            for cara in row:
                line += cara
            print(line, file=output)
        print('</pre></p>', file=output)
        print(f'<p><i>@ {copy}</i></p>', file=output)

        xword = output.getvalue()
        output.close()

        return xword


    def send_mail_text(self, to_email, subject, message, server='smtp.sitex.com.br',
                from_email='noreply@sitex.com.br'):

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ', '.join(to_email)

        msg.set_type('text/html')
        msg.set_content(message)
        msg.add_alternative(message, subtype="html")

        # msg.set_content(message)
        print(msg)

        server = smtplib.SMTP(server, 587)
        server.set_debuglevel(1)
        server.login(from_email, 'Sitex@20171')  # user & password
        server.send_message(msg)
        server.quit()
        print('successfully sent the mail.')


    @intent_file_handler('print.xword.intent')
    def handle_print_xword(self, message):

        data = self.getData()
        while data['size']['rows'] > 15 or data['size']['cols'] > 15:
            data = self.getData()

        puzzle = self.getXwordJob(data)
        self.enclosure.print_text(puzzle)

        solution = self.getXwordMail(data)
        self.send_mail_text(['marcello.yesca@gmail.com'], data['title'], solution)

        self.speak_dialog('print.xword')


    @intent_file_handler('print.hello.intent')
    def handle_print_hello(self, message):
        # self.enclosure.print_command(PrinterCommand.RESET)
        # sleep(1)

        self.enclosure.print_text("Hello World from Brazil!!!", expanded=True)
        sleep(1)

        self.enclosure.print_text("Eu sou a Emilia e agora falo em Português com acentuação, efeitos tipográficos e largura de papel definida!", fancy=True)
        sleep(1)

        self.enclosure.print_text(str(b'\xC9\xCD\xCD\xCD\xBB\x0D\x0A\xBA\x1B\x53\x0012 \x1B\x54\xBA\x0D\x0A\xBA\x20\x20\x20\xBA\x0D\x0A\xC8\xCD\xCD\xCD\xBC\x0D\x0A', 'CP850'))
        sleep(1)
 
        # self.enclosure.print_command(PrinterCommand.RESET)
        self.speak_dialog('print.hello')


    @intent_file_handler('print.picture.intent')
    def handle_print_picture(self, message):
        self.enclosure.print_file("/home/yesca/spike1/fig.txt")
        self.speak_dialog('print.picture')


def create_skill():
    return HelloPrint()
