#!/usr/bin/env python3
import sys

if len(sys.argv) == 2 and sys.argv[1] == "info":
    # Info mode - tell JPAMB about your analyzer
    print("My First Analyzer")        # name
    print("1.0")                      # version  
    print("Student Name")             # group/team
    print("simple,python")            # tags
    print("no")                       # privacy mode - use "yes" to share system info to help us improve
else:
    # Analysis mode - make predictions
    method_name = sys.argv[1]
    
    # Simple strategy: guess everything just works
    print("ok;90%")
    print("divide by zero;10%") 
    print("assertion error;5%")
    print("out of bounds;0%")
    print("null pointer;0%")
    print("*;0%")