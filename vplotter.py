#!/usr/bin/python

import math
import time
import argparse


try:
    import RPi.GPIO as GPIO
    import VPlotterSVG
    isRpi = True
except ImportError:
    print('Not RaspberryPi')
    isRpi = False

if isRpi:
    #Raspberry Pi GPIO Setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Enable pins
    motor1_A_1_pin = 14
    motor1_A_2_pin = 15
    motor1_B_1_pin = 23
    motor1_B_2_pin = 24

    motor2_A_1_pin = 4
    motor2_A_2_pin = 17
    motor2_B_1_pin = 27
    motor2_B_2_pin = 22

    GPIO.setup(motor1_A_1_pin, GPIO.OUT)
    GPIO.setup(motor1_A_2_pin, GPIO.OUT)
    GPIO.setup(motor1_B_1_pin, GPIO.OUT)
    GPIO.setup(motor1_B_2_pin, GPIO.OUT)

    GPIO.setup(motor2_A_1_pin, GPIO.OUT)
    GPIO.setup(motor2_A_2_pin, GPIO.OUT)
    GPIO.setup(motor2_B_1_pin, GPIO.OUT)
    GPIO.setup(motor2_B_2_pin, GPIO.OUT)


#Constants

#Motor 1.8deg/step
stepsPerRev = 200
#5steps/mm => 127steps/inch
stepsPerUnit = 127.0

maxStepSize = 0.5

#Distance between the two motors
c = 32
xStepSize = 1
yStepSize = 1
delay1 = 0.0055
delay2 = 0.0055

#Switch if motor turns the wrong way
reverseMotor1 = False
reverseMotor2 = False

currMotor1Step = 0b1000
currMotor2Step = 0b1000

path = ((10.0, 10.0),
        (10.0, 20.0),
        (20.0, 20.0),
        (20.0, 10.0),
        (10.0, 10.0))

star = ((16, 8), (13, 17), (20, 11), (12, 11), (19, 17), (16, 8))
star2 = ((18, 8), (21, 17), (14, 11), (22, 11), (15, 17), (18, 8))
triangle = ((18, 8), (13, 17), (23, 17), (18, 8))
triangleSmall = ((18, 7), (15, 13), (21, 13), (18, 7))
plumb = ((18, 7), (18, 13), (15, 13), (18, 18), (21, 13), (18, 13))
lowerTriangle = ((18, 13), (15, 19), (21, 19), (18, 13))
upperTriangle = ((18, 13), (15, 7), (21, 7), (18, 13))

a = ((18, 8), (13, 13), (23, 13), (18, 18), (18, 8))

#Set the actual path 
path = star


def main():
    global c, path, gearRadius

    parser = argparse.ArgumentParser(description='V-Plotter for RaspberryPi.')

    parser.add_argument('x', type=float, help='the starting x coordinate')
    parser.add_argument('y', type=float, help='the starting y coordinate')
    parser.add_argument('-c', type=float, default=32.0, help='the starting c coordinate (default: 32.0)')
    parser.add_argument('-r', type=float, default=0.5, help='the motor gear radius (default: 0.5)')
    parser.add_argument('--setup', '-s', dest='setup', action='store_true', default=False,
                        help='find the gear radius (default: False)')
    parser.add_argument('--xml', '-s', dest='xml', default='svg.xml', help='XML SVG')

    args = parser.parse_args()

    print('args:',	args)

    print("Raspberry Pi" if isRpi else "NOT rPi!")

    x1 = args.x
    y1 = args.y
    gearRadius = args.r
    c = args.c

    if args.xml:
        #Read XML; set path
        xml = VPlotterSVG(args.xml)

        if not args.c:
            c = xml.get_c()

        path = xml.get_path()

        if not path:
            print("File " + args.xml + " is empty.")
            return

    if args.setup:
        print("find gear radius")
    else:
        for p in path:
            x2 = float(p[0])
        y2 = float(p[1])
        print("***GOING to Point (", x2, y2, ")***")
        while abs(x1 - p[0]) > maxStepSize or abs(y1 - p[1]) > maxStepSize:
            #If the delta between x1,x2 or y1,y2 is > maxStepSize
            # Then calculate an intermediate destination x,y
            # This will make the line more smooth and limit curving
            if abs(x1 - float(p[0])) > maxStepSize:
                dir_x = -1.0 if x2 < x1 else 1.0
                dir_y = -1.0 if y2 < y1 else 1.0
                x_step = maxStepSize * dir_x

                print(" X step ", x_step)
                y_step = x_step * (y2 - y1) / (x2 - x1)
                x1, y1 = move_to(x1, y1, x1 + x_step, y1 + y_step, c)
            elif abs(y1 - float(p[1])) > maxStepSize:
                dir_x = -1.0 if float(p[0]) < x1 else 1.0
                dir_y = -1.0 if float(p[1]) < y1 else 1.0
                y_step = maxStepSize * dir_y

                print(" Y step ", y_step)
                x_step = y_step * (x2 - x1) / (y2 - y1)
                x1, y1 = move_to(x1, y1, x1 + x_step, y1 + y_step, c)

        #Do this at the end of the looping above so that we ensure we went to the point
        x1, y1 = move_to(x1, y1, float(p[0]), float(p[1]), c)
        print("***WENT to point (", x2, y2, ")***")


#Get L1, L2 based for the point x, y
def getL1L2(x, y, c):
    return math.sqrt((x*x) + (y*y)), math.sqrt( ((c-x)*(c-x)) + (y*y))


#---------------------------------------------------
#Returns delta of L1, and L2
def move_to(x, y, newX, newY, c):
    global gearRadius, stepsPerRev

    currL1, currL2 = getL1L2(x, y, c)
    newL1, newL2 = getL1L2(newX, newY, c)

    steps1 = number_of_steps(newL1 - currL1, gearRadius, stepsPerRev)
    steps2 = number_of_steps(newL2 - currL2, gearRadius, stepsPerRev)
    #the direction
    dir1 = steps1 / abs(steps1) if steps1 != 0.0 else 1.0
    dir2 = steps2 / abs(steps2) if steps2 != 0.0 else 1.0

    print(" **from: (", x, y, ") to ( ", newX, newY, ") steps Motor 1:", dir1, steps1, " steps Motor 2:", dir2, steps2)

    steps1 = abs(steps1)
    steps2 = abs(steps2)

    if isRpi:
        for aa in range(0, (int(round(max(steps1, steps2))))):
            if steps1 > 0:  
#       	    print "spinning motor1 steps remaining:", steps1
                moveSteps(1, dir1, True)
                steps1 -= 1

            if steps2 > 0:
#	        	print "spinning motor2 steps remaining", steps2
                moveSteps(2, dir2, True)
                steps2 -= 1

            if steps1 > 0 and steps2 > 0:
                if steps1 > steps2:
                    s = math.floor(steps1 / steps2)
                    moveSteps(1, s*dir1, True)
                    steps1 -= s
                    print(" *m1 steps remaining:", steps1, " added:", s)
                elif steps2 > steps1:
                    s = math.floor(steps2 / steps1)
                    moveSteps(2, s*dir2, True)
                    steps2 -= s
                    print(" *m2 steps remaining:", steps2, " added:", s)

        return newX, newY

#---------------------------------------------------
if isRpi:
    def set_step1(w1, w2, w3, w4):
        GPIO.output(motor1_A_1_pin, w1)
        GPIO.output(motor1_B_1_pin, w2)
        GPIO.output(motor1_A_2_pin, w3)
        GPIO.output(motor1_B_2_pin, w4)

    def set_step2(w1, w2, w3, w4):
        GPIO.output(motor2_A_1_pin, w1)
        GPIO.output(motor2_B_1_pin, w2)
        GPIO.output(motor2_A_2_pin, w3)
        GPIO.output(motor2_B_2_pin, w4)


#Find number of steps to move arc L
def number_of_steps(L, gear_radius, stepsPerRev):
    deg = (360.0 * L) / (math.pi * gear_radius)
    print("  degrees to rotate: ", deg)
    return deg / (360.0 / stepsPerRev)


def find_radius(L, stepsPerRev, steps):
    return (L * 180.0) / (math.pi * (360.0 * steps / stepsPerRev))

if isRpi:
    def moveSteps(motor, numSteps, turnOff = True):
        try:
            global currMotor1Step, currMotor2Step, delay1, delay2, reverseMotor1, reverseMotor2
            numSteps = int(round(numSteps))

            if (motor == 1 and ((numSteps > 0 and not reverseMotor1) or
                              (numSteps < 0 and reverseMotor1))):
                #Motor 1 spinning +
                for i in range(0, abs(numSteps)):
                    #Set next step
                    currMotor1Step >>= 1
                    if currMotor1Step == 0b0000:
                        currMotor1Step = 0b1000

                    p1 = (currMotor1Step>>3)&1
                    p2 = (currMotor1Step>>2)&1
                    p3 = (currMotor1Step>>1)&1
                    p4 = currMotor1Step&1

                    print('    output to motor 1+', p1, p2, p3, p4)
                    GPIO.output(motor1_A_1_pin, p1)
                    GPIO.output(motor1_B_1_pin, p2)
                    GPIO.output(motor1_A_2_pin, p3)
                    GPIO.output(motor1_B_2_pin, p4)

                    time.sleep(delay1)

            elif motor == 1 and ((numSteps > 0 and reverseMotor1) or\
                                (numSteps < 0 and not reverseMotor1) ):
                #Motor 1 spinning -
                for i in range(0, abs(numSteps)):
                    #Set next step
                    currMotor1Step >>= 1
                    if currMotor1Step == 0b0000:
                        currMotor1Step = 0b1000

                    p1 = currMotor1Step&1
                    p2 = (currMotor1Step>>1)&1
                    p3 = (currMotor1Step>>2)&1
                    p4 = (currMotor1Step>>3)&1

                    print('    output to motor 1-', p1, p2, p3, p4)
                    GPIO.output(motor1_A_1_pin, p1)
                    GPIO.output(motor1_B_1_pin, p2)
                    GPIO.output(motor1_A_2_pin, p3)
                    GPIO.output(motor1_B_2_pin, p4)

                    time.sleep(delay1)

			elif (motor == 2 and ((numSteps > 0 and not reverseMotor2) or (numSteps < 0 and reverseMotor2))):
                #Motor 2 spinning +
                for i in range(0, abs(numSteps)):
                    #Set next step
                    currMotor2Step >>= 1
                    if currMotor2Step == 0b0000:
                        currMotor2Step = 0b1000

                    p1 = (currMotor2Step >> 3) & 1
                    p2 = (currMotor2Step >> 2) & 1
                    p3 = (currMotor2Step >> 1) & 1
                    p4 = currMotor2Step & 1

                    print('    output to motor 2+', p1, p2, p3, p4)
                    GPIO.output(motor2_A_1_pin, p1)
                    GPIO.output(motor2_B_1_pin, p2)
                    GPIO.output(motor2_A_2_pin, p3)
                    GPIO.output(motor2_B_2_pin, p4)

                    time.sleep(delay2)

			elif (motor == 2 and ((numSteps > 0 and reverseMotor2) or (numSteps < 0 and not reverseMotor2))):
                for i in range(0, abs(numSteps)):
                    #Motor 2 spinning -
                    #Set next step
                    currMotor2Step >>= 1
                    if currMotor2Step == 0b0000:
                        currMotor2Step = 0b1000

                    p1 = currMotor2Step & 1
                    p2 = (currMotor2Step >> 1) & 1
                    p3 = (currMotor2Step >> 2) & 1
                    p4 = (currMotor2Step >> 3) & 1

                    print('    output to motor 2-', p1, p2, p3, p4)
                    GPIO.output(motor2_A_1_pin, p1)
                    GPIO.output(motor2_B_1_pin, p2)
                    GPIO.output(motor2_A_2_pin, p3)
                    GPIO.output(motor2_B_2_pin, p4)

                    time.sleep(delay2)

        finally:
            #TURN OFF! SO MOTOR AND CONTROLLER DON'T OVERHEAT!!
            if turnOff:
                GPIO.output(motor1_A_1_pin, 0)
                GPIO.output(motor1_B_1_pin, 0)
                GPIO.output(motor1_A_2_pin, 0)
                GPIO.output(motor1_B_2_pin, 0)

                GPIO.output(motor2_A_1_pin, 0)
                GPIO.output(motor2_B_1_pin, 0)
                GPIO.output(motor2_A_2_pin, 0)
                GPIO.output(motor2_B_2_pin, 0)


try:
    main()
except Exception as e:
    print(e)
finally:
    if isRpi:
        set_step1(0, 0, 0, 0)
        set_step2(0, 0, 0, 0)

