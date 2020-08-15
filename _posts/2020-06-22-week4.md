---
layout: post
title: Week 4
---

Week 4: June 22 to June 26

This week I was able to find a solution for one of the two main parts of week 3.
I believe that we could use the platform created by always ai to develop the people detection part of the code.
More information’s about this can be found at:
http://alwaysai.co

Using their Realtime object detection code we can potentially deploy this to raspberry pi and use it to detect in Realtime whenever a person is identified.
For the distance parts I am working in two different ideas.
1. Disparity maps. Using them we could identify the distance between object A to object B and scaling that treat object A as the camera and B as the person.
2. We could also use the idea of bounding boxes to determine a ratio between the distance that the person is and the area of the bounding box. With a simple formula we could derive a system to identify the distance in meters.

