import sys, os
sys.path.insert(0, '../../..')
from django.core.management import setup_environ
from ngt import settings
setup_environ(settings)
from subprocess import Popen

from ngt.assets.models import Asset
import moc_stage

"""
testids = [
    "M03/05609",
    "M03/05590",
    "M03/05571",
    "M03/05561",
    "M03/05576",
    "M03/05586",

]
count = 0
for id in testids:
    count += 1
    print "Start ", count
    a = Asset.objects.get(product_id=id)
    try:
        #moc_stage.stage_image(a.file_path, output_dir='testdata/')
        outfile = 'out/'+os.path.splitext(os.path.basename(a.file_path))[0]+'.cub'
        moc_stage.mocproc(a.file_path, outfile, map='PolarStereographic')
    except AssertionError, e:
        print e
    print "Finish ", count
"""
testids = [
    'S21/01438',
    'M01/04564',
    'E01/01883',
    'M22/01571',
    'M21/00236',
    'M22/02026',
    'M01/04331',
    'S21/01071',
    'E01/01402',
    'S21/00337',
]
count = 0
for id in testids:
    count += 1
    print "Start ", count
    try:
        a = Asset.objects.get(class_label='mocprocd moc image', product_id=id)
    except Asset.DoesNotExist:
        print "%s NOT FOUND!" % id
        continue
    try:
        #moc_stage.stage_image(a.file_path, output_dir='testdata/')
        outfile = 'polartest_8bit/'+os.path.splitext(os.path.basename(a.file_path))[0]+'_8bit.cub'
        #moc_stage.mocproc(a.file_path, outfile, map='PolarStereographic')
        p = Popen(['./scale2int8.py', a.file_path, outfile])
        p.wait()
    except AssertionError, e:
        print e
    print "Finish ", count
