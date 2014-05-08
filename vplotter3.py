#!/usr/bin/python

import sys, math, time, argparse, random


try:
	import RPi.GPIO as GPIO
	isRpi = True
except ImportError:
	print 'Not RaspberryPi'
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
stepsPerRev = 200 #Motor 1.8deg/step
stepsPerUnit = 127.0 #5steps/mm => 127steps/inch

xOrigin = 0.0
yOrigin = 0.0
l1 = 0.0
l2 = 0.0
l3 = 32.0 #Distance between the two motors
delay1 = 0.0055
delay2 = 0.0055
reverseMotor1 = False #Switch if motor turns the wrong way
reverseMotor2 = False #Switch if motor turns the wrong way

xMin = 6.0
xMax = 16.0

yMin = 10.0
yMax = 25.0

currMotor1Step = 0b1000
currMotor2Step = 0b1000


#CS 20140405
#This algorithm bounces around within the specified box


def main():
    global c, l1, l2, l3, xOrigin, yOrigin, stepsPerUnit

    parser = argparse.ArgumentParser(description='V-Plotter for RaspberryPi.')

    parser.add_argument('x', type=float, help='the starting x')
    parser.add_argument('y', type=float, help='the starting y')
    parser.add_argument('-l3', type=float, default=32.0, help='the starting l3 (default: 32.0)')
    parser.add_argument('--setup', '-s', dest='setup', action='store_true', default=False, help='find the gear radius (default: False)')
    
    args = parser.parse_args()
		
    print 'args:',	args

    print "Raspberry Pi" if isRpi else "FAKE!"

    xOrigin = args.x
    yOrigin = args.y
    l3 = args.l3
    type = 'pong'

    l1, l2 = getL1L2(xOrigin, yOrigin, l3)

    leftWall = 13.0
    rightWall = 23.0
    topWall = 9.0
    bottomWall = 19.0
	
    if args.setup:
        print "find gear radius"
    else:
        dir1 = 1 if random.randint(0,1) == 1 else -1
        dir2 = 1 if random.randint(0,1) == 1 else -1

        #Initialize vars
        v_x = random.randint(0,1)

        l1StepsFromOrigin = 0 #Tracks steps since starting
        l2StepsFromOrigin = 0

        while v_x >= 0:
            #move a step then check if we hit an edge
            move = True
            leaveEdge = 2 #Needed so the motors don't get stuck at an edge
            print '  v_x:', v_x, dir1, dir2

            while move:
                hit = checkHit(l1StepsFromOrigin, l2StepsFromOrigin) # > 0 if hit

                if hit > 0 and leaveEdge <= 0 : #There was a HIT! AKA Switch dir / motor
                    move = False
                    print ' switching motors', getXY(l1+(l1StepsFromOrigin/stepsPerUnit), l2+(l2StepsFromOrigin/stepsPerUnit), l3)
                    print '  l1, l2', l1StepsFromOrigin, l2StepsFromOrigin   
                    if type == 'rect':
                        print '   rect style bounce', hit
                        if v_x % 2 == 1: #odd l1 motor was moving and hit an edge
                            dir1 = dir1 * -1
                        else: #even - l2 motor was moving and hit an edge
                            dir2 = dir2 * -1
                    else: # do pong style
                        print '   pong style bounce', hit
                        if v_x % 2 == 1: #odd l1 motor was moving and hit an edge
                            if hit == 1: #top
                                dir2 = 1
                            elif hit == 2: #right
                                dir2 = 1 #????
                            elif hit == 3: #bottom
                                dir2 = -1
                            elif hit == 4: #left
                                dir2 = -1 #??????????
                        else: #even - l2 motor was moving and hit an edge
                            if hit == 1: #top
                                dir1 = 1
                            elif hit == 2: #right
                                dir1 = -1
                            elif hit == 3: #bottom
                                dir1 = -1
                            elif hit == 4: #left
                                dir1 = 1
                else:
                    if v_x % 2 == 1: #odd -  l1 motor
                        moveSteps(1, dir1)
                        l1StepsFromOrigin = l1StepsFromOrigin + dir1
                    else: #even - l2 motor                        
                        moveSteps(2, dir2)
                        l2StepsFromOrigin = l2StepsFromOrigin + dir2

                leaveEdge = leaveEdge - 1 #This is needed so we don't get stuck at the edge

            v_x = v_x + 1

#Returns the edge of the rectangle hit 1 => top, 2 => right, 3 => bottom, 4 => left
def checkHit(l1StepsFromOrigin, l2StepsFromOrigin):
    global l1, l2, l3, xOrigin, yOrigin, stepsPerUnit, xMin, xMax, yMin, yMax #127steps/inch

    #print ' check hit'

    x, y = getXY(l1+(l1StepsFromOrigin/stepsPerUnit), l2+(l2StepsFromOrigin/stepsPerUnit), l3)

    if y < yMin:
        return 1
    elif x > xMax:
        return 2
    elif y > yMax:
        return 3
    elif x < xMin:
        return 4
    else:
        return 0

#Get L1, L2 based for the point x, y
def getL1L2(x, y, c):
    return math.sqrt((x*x) + (y*y)), math.sqrt( ((c-x)*(c-x)) + (y*y))

#Get x y based on l1, l2, and l3
def getXY (l1, l2, l3):
    x = ((l1*l1) - (l2*l2) + (l3*l3)) / (2*l3)
    #print ' getXY', l1, x
    y = math.sqrt( (l1*l1) - (x*x) )
    return x, y

#---------------------------------------------------
if isRpi:
	def setStep1(w1, w2, w3, w4):
		GPIO.output(motor1_A_1_pin, w1)
		GPIO.output(motor1_B_1_pin, w2)
		GPIO.output(motor1_A_2_pin, w3)
		GPIO.output(motor1_B_2_pin, w4)

if isRpi:
	def moveSteps(motor, numSteps, turnOff = True):
		try:	
			global currMotor1Step, currMotor2Step, delay1, delay2, reverseMotor1, reverseMotor2
			numSteps = int(round(numSteps))
			#currMotor1Step = 0b1000
			#currMotor2Step = 0b1000
#			print 'moving motor:', motor, ' steps:', numSteps, ' rev1:', reverseMotor1, ' rev2:', reverseMotor2, ' delay1:', delay1, ' delay2:', delay2

			if motor == 1 and ((numSteps > 0 and not reverseMotor1) or\
					(numSteps < 0 and reverseMotor1) ): #Motor 1 spinning +
				for i in range(0, abs(numSteps)):
					#Set next step
					currMotor1Step = currMotor1Step>>1
					if currMotor1Step == 0b0000:
						currMotor1Step = 0b1000

					p1 = (currMotor1Step>>3)&1
					p2 = (currMotor1Step>>2)&1
					p3 = (currMotor1Step>>1)&1
					p4 = currMotor1Step&1
					
					#print '    output to motor 1+',p1,p2,p3,p4
					GPIO.output(motor1_A_1_pin, p1)
					GPIO.output(motor1_B_1_pin, p2)
					GPIO.output(motor1_A_2_pin, p3)
					GPIO.output(motor1_B_2_pin, p4)
					
					time.sleep(delay1)

			elif motor == 1 and ((numSteps > 0 and reverseMotor1) or\
					(numSteps < 0 and not reverseMotor1) ): #Motor 1 spinning -
				for i in range(0, abs(numSteps)):
					#Set next step
					currMotor1Step = currMotor1Step>>1
					if currMotor1Step == 0b0000:
						currMotor1Step = 0b1000

					p1 = currMotor1Step&1
					p2 = (currMotor1Step>>1)&1
					p3 = (currMotor1Step>>2)&1
					p4 = (currMotor1Step>>3)&1

					#print '    output to motor 1-',p1,p2,p3,p4
					GPIO.output(motor1_A_1_pin, p1)
					GPIO.output(motor1_B_1_pin, p2)
					GPIO.output(motor1_A_2_pin, p3)
					GPIO.output(motor1_B_2_pin, p4)
					
					time.sleep(delay1)
			elif motor == 2 and ((numSteps > 0 and not reverseMotor2) or\
					(numSteps < 0 and reverseMotor2) ): #Motor 2 spinning +
				for i in range(0, abs(numSteps)):
					#Set next step
					currMotor2Step = currMotor2Step>>1
					if currMotor2Step == 0b0000:
						currMotor2Step = 0b1000

					p1 = (currMotor2Step>>3)&1
					p2 = (currMotor2Step>>2)&1
					p3 = (currMotor2Step>>1)&1
					p4 = currMotor2Step&1

					#print '    output to motor 2+        ',p1,p2,p3,p4
					GPIO.output(motor2_A_1_pin, p1)
					GPIO.output(motor2_B_1_pin, p2)
					GPIO.output(motor2_A_2_pin, p3)
					GPIO.output(motor2_B_2_pin, p4)
				
					time.sleep(delay2)
			elif motor == 2 and ((numSteps > 0 and reverseMotor2) or\
					(numSteps < 0 and not reverseMotor2) ): #Motor 2 spinning -
				for i in range(0, abs(numSteps)):
					#Set next step
					currMotor2Step = currMotor2Step>>1
					if currMotor2Step == 0b0000:
						currMotor2Step = 0b1000

					p1 = currMotor2Step&1
					p2 = (currMotor2Step>>1)&1
					p3 = (currMotor2Step>>2)&1
					p4 = (currMotor2Step>>3)&1

					#print '    output to motor 2-        ',p1,p2,p3,p4
					GPIO.output(motor2_A_1_pin, p1)
					GPIO.output(motor2_B_1_pin, p2)
					GPIO.output(motor2_A_2_pin, p3)
					GPIO.output(motor2_B_2_pin, p4)

					time.sleep(delay2)

		finally:
#			print 'turning off motors'
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
	print e
finally:
	if isRpi:
		setStep1(0,0,0,0)

