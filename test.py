from dlstorage.utils.benchmark import *
from dlstorage.utils.vdmsbench import *

vd = VDMSStorageManager(TestTagger())
#p2 = VDMSPerfTest(vd, 'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4')
p2 = VDMSPerfTest(vd, 'f65sec.mp4')
p2.runAll()
