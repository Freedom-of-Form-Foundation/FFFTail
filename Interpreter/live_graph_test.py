#live_graph_test
#equivalent of coding scratch paper, various bits of code from matplotlibs docs
#Testing various aspects of the animation library

'''
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random

#figure
fig, ax = plt.subplots()
#save background for faster graphing using blit
background = fig.canvas.copy_from_bbox(ax.bbox)
#the data
xs = []
ys = []

#this function is called periodically from FuncAnimation
def animate(i, xs, ys):

    #read temperature (Celsius) from TMP102
    rand_y = random.random()

    #add x and y to lists
    xs.append(dt.datetime.now().strftime('%S.%f'))
    ys.append(rand_y)

    #limit x and y lists to 20 items
    xs = xs[-50:]
    ys = ys[-50:]

    #save the background for blit code
    #fig.canvas.restore_region(background)
    
    #draw x and y lists
    ax.clear()
    points = ax.plot(xs, ys)

    #formatting stuff
    plt.xticks(rotation=45, ha='right')
    plt.subplots_adjust(bottom=0.30)
    plt.title('Random Value from random()')
    plt.ylabel('Value')
    #plt.locator_params(axis='x', nbins=10) #limit the number of points on the x axis

#set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=100) #, blit=True, save_count=50)
plt.show()


import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random

fig, ax = plt.subplots()

x = np.arange(0, 2*np.pi, 0.01)
line, = ax.plot(x, np.sin(x))
ys = []

def animate(i):
    global ys
    rand_y = random.random()
    ys.append(rand_y) #add random y value to our line
    ys = ys[-50:]
    line.set_ydata(ys)  # update the data.
    return line,


ani = animation.FuncAnimation(
    fig, animate, interval=20, blit=True, save_count=50)

# To save the animation, use e.g.
#
# ani.save("movie.mp4")
#
# or
#
# writer = animation.FFMpegWriter(
#     fps=15, metadata=dict(artist='Me'), bitrate=1800)
# ani.save("movie.mp4", writer=writer)

plt.show()
'''
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Fixing random state for reproducibility
np.random.seed(19680801)


def random_walk(num_steps, max_step=0.05):
    """Return a 3D random walk as (num_steps, 3) array."""
    start_pos = np.random.random(3)
    steps = np.random.uniform(-max_step, max_step, size=(num_steps, 3))
    walk = start_pos + np.cumsum(steps, axis=0)
    return walk


def update_lines(num, walks, lines):
    for line, walk in zip(lines, walks):
        # NOTE: there is no .set_data() for 3 dim data...
        line.set_data(walk[:num, :2].T)
        line.set_3d_properties(walk[:num, 2])
    return lines


# Data: 40 random walks as (num_steps, 3) arrays
num_steps = 300
walks = [random_walk(num_steps) for index in range(40)]

# Attaching 3D axis to the figure
fig = plt.figure()
ax = fig.add_subplot(projection="3d")

# Create lines initially without data
lines = [ax.plot([], [], [])[0] for _ in walks]

# Setting the axes properties
ax.set(xlim3d=(0, 1), xlabel='X')
ax.set(ylim3d=(0, 1), ylabel='Y')
ax.set(zlim3d=(0, 1), zlabel='Z')

# Creating the Animation object
ani = animation.FuncAnimation(
    fig, update_lines, num_steps, fargs=(walks, lines), interval=100)

plt.show()
