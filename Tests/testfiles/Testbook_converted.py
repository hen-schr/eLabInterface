
# make sure that the script is always executed in the same directory as where the script itself is stored
import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import numpy as np


# # Heading

# In[ ]:


for i in range(0, 10):
    print(i)


# In[ ]:


# 