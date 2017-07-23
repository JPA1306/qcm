import os
from main import Elearn
from datetime import date

try: os.remove('a.db')
except: pass

elearn = Elearn('sqlite:///a.db')
elearn.test_fill(
  chapter='Météorologie et aérologie',
  lquestion=(
    ('questions/Meteorologie/caea-2015/Q01.png','abcd','a'),
    ('questions/Meteorologie/caea-2015/Q02.png','abcd','d'),
    ('questions/Meteorologie/caea-2015/Q03.png','abcd','d'),
    ('questions/Meteorologie/caea-2015/Q04.png','abcd','b'),
    ('questions/Meteorologie/caea-2015/Q05.png','abcd','a'),
    ('questions/Meteorologie/caea-2015/Q06.png','abcd','c'),
    ('questions/Meteorologie/caea-2015/Q07.png','abcd','b'),
  )
)

Q = elearn.new_questionnaire(
    date=date(2017,2,19),
    title='test exam',
    nb_question=4,
    lstudent=('Barack Obama','Bill Clinton','John Kennedy','Franklin Roosevelt'),
)
Q.create_papers('b.pdf')
