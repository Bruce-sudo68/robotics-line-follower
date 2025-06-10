# Line-Following Robot Simulation

I built this simple line-following robot simulation in Python using Pygame over the course of a few days. The goal was to challenge myself to go from idea to working code and get a better feel for how robots process sensor data and follow paths.

It’s not perfect—after the first turn, the robot starts to wobble and slows down. I tried to fix it but couldn’t fully figure it out yet, which honestly taught me even more. It pushed me to think about real-world control problems and the trial-and-error that comes with robotics.

It’s a small project, but it shows that I’m serious about learning, experimenting, and improving with every step.

### What I Learned
- Reading “sensor” data by sampling pixel colors  
- Implementing basic steering and feedback loops  
- Debugging quirks like wobble and slowdown

### How to Run
```bash
git clone https://github.com/Bruce-sudo68/robotics-line-follower
cd robotics-line-follower
pip install pygame
python main.py
