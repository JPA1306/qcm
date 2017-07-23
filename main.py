from pathlib import Path

#===============================================================================
def initialise(metadata):
#===============================================================================
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
    Column('rank',Integer(),nullable=False),
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

#===============================================================================
class Elearn:
#===============================================================================

#-------------------------------------------------------------------------------
  def __init__(self,dburl):
#-------------------------------------------------------------------------------
    from sqlalchemy import create_engine, MetaData
    self.eng = eng = create_engine(dburl)
    self.metadata = metadata = MetaData(bind=eng)
    metadata.reflect()
    if not metadata.tables: initialise(metadata); metadata.create_all()
    self.__dict__.update(metadata.tables)

#-------------------------------------------------------------------------------
  def test_fill(self,chapter,lquestion,mmpp=.25):
#-------------------------------------------------------------------------------
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

#-------------------------------------------------------------------------------
  def new_questionnaire(self,date,title,nb_question,lstudent):
#-------------------------------------------------------------------------------
    from sqlalchemy import select,func
    def qdvalues(header=20,footer=10,respa=8,interq=5):
      page = 1; y = header; maxy = 297-footer
      selc = (self.Question.c.oid,self.Question.c.height)
      for i,(question_oid,height) in enumerate(conn.execute(select(selc).order_by(func.random()).limit(nb_question)),1):
        h = height+respa
        assert header+h < maxy
        yp = y+h
        if yp>maxy: page += 1; y = header; yp = y+h+interq
        else: yp += interq
        yield {'questionnaire':questionnaire_oid,'question':question_oid,'rank':i,'page':page,'offset':y}
        y = yp
    with self.eng.begin() as conn:
      questionnaire_oid = conn.execute(self.Questionnaire.insert().values({'date':date,'title':title})).inserted_primary_key[0]
      conn.execute(self.QuestionnaireDefn.insert(),list(qdvalues()))
      conn.execute(self.Paper.insert(),[{'questionnaire':questionnaire_oid,'student':student} for student in lstudent])
    return Questionnaire(self,questionnaire_oid)

#===============================================================================
class Questionnaire:
#===============================================================================

#-------------------------------------------------------------------------------
  def __init__(self,elearn,oid):
#-------------------------------------------------------------------------------
    from sqlalchemy import select
    from sqlalchemy.sql import and_
    self.oid = oid
    with elearn.eng.begin() as conn:
      selc = (elearn.Questionnaire.c.date,elearn.Questionnaire.c.title)
      cond = elearn.Questionnaire.c.oid==oid
      self.date,self.title = conn.execute(select(selc).where(cond)).fetchone()
      selc = (
        elearn.Chapter.c.title,
        elearn.Question.c.answers,
        elearn.Question.c.correct,
        elearn.Question.c.content,
        elearn.Question.c.format,
        elearn.Question.c.width,
        elearn.Question.c.height,
        elearn.QuestionnaireDefn.c.rank,
        elearn.QuestionnaireDefn.c.page,
        elearn.QuestionnaireDefn.c.offset,
        )
      cond = and_(
        elearn.QuestionnaireDefn.c.questionnaire==oid,
        elearn.Question.c.oid==elearn.QuestionnaireDefn.c.question,
        elearn.Chapter.c.oid==elearn.Question.c.chapter,
        )
      sortc = elearn.QuestionnaireDefn.c.rank
      self.questions = conn.execute(select(selc).where(cond).order_by(sortc)).fetchall()
      selc = (elearn.Paper.c.oid,elearn.Paper.c.student)
      cond = elearn.Paper.c.questionnaire==oid
      self.papers = conn.execute(select(selc).where(cond)).fetchall()

#-------------------------------------------------------------------------------
  def dump_paper(self,paper,target):
#-------------------------------------------------------------------------------
    from lxml.etree import tostring as tobytes
    from lxml.builder import ElementMaker
    from base64 import b64encode
    from io import BytesIO
    from PyPDF2 import PdfFileReader
    from cairosvg import svg2pdf
    def dump(): target.appendPagesFromReader(PdfFileReader(BytesIO(svg2pdf(tobytes(svg)))))
    E = ElementMaker(namespace='http://www.w3.org/2000/svg',nsmap={'xlink':'http://www.w3.org/1999/xlink'})
    pagetotal = self.questions[-1].page; page = None; svg = None
    for q in self.questions:
      if q.page != page:
        if svg is not None: dump()
        page = q.page
        svg = E.svg(
          E.text(self.title,x='10mm',y='5mm',style='font-size:.8em; text-anchor:start;'),
          E.text(str(self.date),x='105mm',y='5mm',style='font-size:.8em; text-anchor:middle;'),
          E.text('{0.oid}:{0.student}'.format(paper),x='200mm',y='5mm',style='font-size:.8em; text-anchor:end;'),
          E.text('{}/{}'.format(page,pagetotal),x='105mm',y='292mm',style='font-size:.8em; text-anchor:middle;'),
          width='210mm',
          height='297mm',
          )
      svg.append(E.text('{:3d}.'.format(q.rank),x='17mm',y='{}mm'.format(q.offset+2),style='font-size:.8em; text-anchor:end;'))
      img = E.image(x='20mm',y='{}mm'.format(q.offset),width='{}mm'.format(q.width),height='{}mm'.format(q.height))
      img.set('{http://www.w3.org/1999/xlink}href','data:image/{};base64,{}'.format(q.format.lower(),b64encode(q.content).decode('utf-8')))
      svg.append(img)
      offset = q.offset+q.height+3
      ya = '{}mm'.format(offset)
      yb = '{}mm'.format(offset+1)
      for i,a in enumerate(q.answers):
        svg.append(E.text(a,x='{}mm'.format(27+i*4),y=ya,style='font-size:.8em; text-anchor:middle;'))
        svg.append(E.rect(x='{}mm'.format(25+i*4),y=yb,width='4mm',height='4mm',fill='white',stroke='black'))
    dump()

#-------------------------------------------------------------------------------
  def create_papers(self,path):
#-------------------------------------------------------------------------------
    from PyPDF2 import PdfFileWriter
    target = PdfFileWriter()
    for p in self.papers: self.dump_paper(p,target)
    with open(path,'wb') as v: target.write(v)

#===============================================================================
def zealouscrop(x,thr=255):
#===============================================================================
  from numpy import array, any, nonzero
  a = array(x.convert('L'))
  a0 = nonzero(any(a<thr,axis=0))[0]; a1 = nonzero(any(a<thr,axis=1))[0]
  # crop box: left,upper,right,lower
  return x.crop((a0[0],a1[0],a0[-1],a1[-1]))
