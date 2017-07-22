# File:           {filename}
# Creation date:  {today}
# Contributors:   Jean-Marc Andreoli
# Language:       python
# Purpose:        {purpose}
#

from pathlib import Path
from collections import namedtuple

def initialise(metadata):
  from sqlalchemy import Table, Column, ForeignKey
  from sqlalchemy.types import Integer, Float, Unicode, Date, Enum, BLOB
  Table(
    'Chapter',metadata,
    Column('oid',Integer(),primary_key=True),
    Column('title',Unicode(),nullable=False),
    )
  Table(
    'Question',metadata,
    Column('oid',Integer(),primary_key=True),
    Column('content',BLOB(),nullable=False),
    Column('format',Enum('PNG','TIFF','GIF','JPEG'),nullable=False),
    Column('width',Integer(),nullable=False),
    Column('height',Integer(),nullable=False),
    Column('chapter',ForeignKey('Chapter.oid'),nullable=False),
    Column('answers',Unicode(),nullable=False),
    Column('correct',Unicode(1),nullable=False),
    )
  Table(
    'Questionnaire',metadata,
    Column('oid',Integer(),primary_key=True),
    Column('date',Date(),nullable=False),
    Column('title',Unicode(),nullable=False),
    )
  Table(
    'QuestionnaireDefn',metadata,
    Column('oid',Integer(),primary_key=True),
    Column('questionnaire',ForeignKey('Questionnaire.oid'),nullable=False),
    Column('question',ForeignKey('Question.oid'),nullable=False),
    Column('page',Integer(),nullable=False),
    Column('offset',Float(),nullable=False),
    )
  Table(
    'Paper',metadata,
    Column('oid',Integer(),primary_key=True),
    Column('student',Unicode(),nullable=False),
    Column('questionnaire',ForeignKey('Questionnaire.oid'),nullable=False),
    )
  Table(
    'PaperAnswer',metadata,
    Column('oid',Integer(),primary_key=True),
    Column('paper',ForeignKey('Paper.oid'),nullable=False),
    Column('answer',Unicode(1),nullable=False),
    )

class Elearn:

  def __init__(self,dburl):
    from sqlalchemy import create_engine, MetaData
    self.eng = eng = create_engine(dburl)
    self.metadata = metadata = MetaData(bind=eng)
    metadata.reflect()
    if not metadata.tables: initialise(metadata); metadata.create_all()
    self.__dict__.update(metadata.tables)

  def test_fill(self,chapter,lquestion,mmpp=.25):
    def qvalues():
      from PIL import Image
      from io import BytesIO
      for path,answers,correct in lquestion:
        with Image.open(path) as img, BytesIO() as buf:
          format = img.format
          img = zealouscrop(img)
          img.save(buf,format=format)
          content = buf.getvalue()
          width,height = img.size
        yield {'chapter':chapter_oid,'answers':answers,'correct':correct,'content':content,'width':mmpp*width,'height':mmpp*height,'format':format}
    with self.eng.begin() as conn:
      chapter_oid = conn.execute(self.Chapter.insert().values({'title':chapter})).inserted_primary_key[0]
      if lquestion: conn.execute(self.Question.insert(),list(qvalues()))

  def new_questionnaire(self,date,title,nb_question,lstudent):
    from sqlalchemy import select,func
    from numpy.random import shuffle
    def qdvalues(header=50,footer=10,respa=15,interq=3):
      from numpy import array,cumsum,hstack
      page = 0; y = header; maxy = 297-footer
      for question_oid,height in conn.execute(select((self.Question.c.oid,self.Question.c.height)).order_by(func.random()).limit(nb_question)):
        h = height+respa
        assert header+h < maxy
        yp = y+h
        if yp>maxy: page += 1; y = header; yp = y+h+interq
        else: yp += interq
        yield {'questionnaire':questionnaire_oid,'question':question_oid,'page':page,'offset':y}
        y = yp
    with self.eng.begin() as conn:
      questionnaire_oid = conn.execute(self.Questionnaire.insert().values({'date':date,'title':title})).inserted_primary_key[0]
      conn.execute(self.QuestionnaireDefn.insert(),list(qdvalues()))
      conn.execute(self.Paper.insert(),[{'questionnaire':questionnaire_oid,'student':student} for student in lstudent])
    return Questionnaire(self,questionnaire_oid)

Question = namedtuple('Question','chapter answers correct content format width height page offset'.split())
Paper = namedtuple('Paper','oid student'.split())

class Questionnaire:

  def __init__(self,elearn,oid):
    from sqlalchemy import select
    from sqlalchemy.sql import and_
    self.oid = oid
    with elearn.eng.begin() as conn:
      self.date,self.title = conn.execute(select((elearn.Questionnaire.c.date,elearn.Questionnaire.c.title)).where(elearn.Questionnaire.c.oid==oid)).fetchone()
      self.questions = [Question(*r) for r in conn.execute(select((elearn.Chapter.c.title,elearn.Question.c.answers,elearn.Question.c.correct,elearn.Question.c.content,elearn.Question.c.format,elearn.Question.c.width,elearn.Question.c.height,elearn.QuestionnaireDefn.c.page,elearn.QuestionnaireDefn.c.offset)).where(and_(elearn.QuestionnaireDefn.c.questionnaire==oid,elearn.Question.c.oid==elearn.QuestionnaireDefn.c.question,elearn.Chapter.c.oid==elearn.Question.c.chapter)))]
      self.papers = [Paper(*r) for r in conn.execute(select((elearn.Paper.c.oid,elearn.Paper.c.student)).where(elearn.Paper.c.questionnaire==oid))]

  def create_paper(self,student):
    from lxml.etree import tostring as tobytes
    from lxml.builder import E
    from base64 import b64encode
    from io import BytesIO
    from PyPDF2 import PdfFileReader, PdfFileWriter
    from cairosvg import svg2pdf
    def svgbase(page):
      return E.SVG(
        E.TEXT(self.title,x='10mm',y='15mm',**{'text-anchor':'start'}),
        E.TEXT(str(self.date),x='105mm',y='15mm',**{'text-anchor':'middle'}),
        E.TEXT(student,x='200mm',y='15mm',**{'text-anchor':'end'}),
        E.TEXT('{}/{}'.format(page,pagetotal),x='105mm',y='292mm',**{'text-anchor':'middle'}),
        width='210mm',
        height='297mm',
        xmlns='http://www.w3.org/2000/svg',
        )
    def dump():
      t.appendPagesFromReader(PdfFileReader(BytesIO(svg2pdf(tobytes(svg)))))
    page = None; pagetotal = self.questions[-1].page; svg = None
    t = PdfFileWriter()
    for q in self.questions:
      if q.page != page:
        if svg is not None: dump()
        page = q.page
        svg = svgbase(page)
      img = E.IMAGE(x='15mm',y='{}mm'.format(q.offset))
      img.set('{http://www.w3.org/1999/xlink}href','data:image/{};base64,{}'.format(q.format.lower(),b64encode(q.content).decode('utf-8')))
      svg.append(img)
    dump()
    self.paper = svg
    with BytesIO() as v: t.write(v); return v.getvalue()

  def create_papers(self): pass

def zealouscrop(x,thr=255):
  from numpy import array, any, nonzero
  a = array(x.convert('L'))
  a0 = nonzero(any(a<thr,axis=0))[0]; a1 = nonzero(any(a<thr,axis=1))[0]
  # crop box: left,upper,right,lower
  return x.crop((a0[0],a1[0],a0[-1],a1[-1]))
