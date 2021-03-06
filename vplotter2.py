#!/usr/bin/python

import sys, math, time, argparse


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

maxStepSize = 0.5
c = 32 #Distance between the two motors
xStepSize = 1 #
yStepSize = 1 #
delay1 = 0.0055
delay2 = 0.0055
reverseMotor1 = False #Switch if motor turns the wrong way
reverseMotor2 = False #Switch if motor turns the wrong way

currMotor1Step = 0b1000
currMotor2Step = 0b1000

path = ((10.0,10.0),
(10.0, 20.0),
		(20.0, 20.0),
		(20.0, 10.0),
		(10.0, 10.0)
		)

star = ((18, 8), (15,17), (22,11), (14,11), (21,17), (18,8))
star2 = ((18, 8), (21,17), (14,11), (22,11), (15,17), (18,8))
triangle = ((18,8), (13,17), (23,17), (18,8))
triangleSmall = ((18,7), (15,13), (21,13), (18,7))
plumb = ((18,7),(18,13),(15,13),(18,18),(21,13),(18,13))
lowerTriangle = ((18,13),(15,19),(21,19),(18,13))
upperTriangle = ((18,13),(15,7),(21,7),(18,13))

a = ((18,8),(13,13),(23,13),(18,18),(18,8))
#Set the actual path 
path = a

def main():
	global c, path, gearRadius

	parser = argparse.ArgumentParser(description='V-Plotter for RaspberryPi.')

	parser.add_argument('x', type=float, help='the starting x coordinate')
	parser.add_argument('y', type=float, help='the starting y coordinate')
	parser.add_argument('-c', type=float, default=32.0, help='the starting c coordinate (default: 32.0)')
	parser.add_argument('-r', type=float, default=0.5, help='the motor gear radius (default: 0.5)')
	parser.add_argument('--setup', '-s', dest='setup', action='store_true', default=False, help='find the gear radius (default: False)')

	args = parser.parse_args()
		
	print 'args:',	args

	print "Raspberry Pi" if isRpi else "FAKE!"

	x1 = args.x
	y1 = args.y
	gearRadius = args.r
	c = args.c
	
	if args.setup:
	    print "find gear radius"
	else:
            for a in range(1,2):
                x = 10
                while x > 0:
                    inches = x
                    numSteps = stepsPerUnit * inches
                    dir = -1 if x % 2 == 1 else 1
                    moveSteps(a, numSteps * dir)
                    moveSteps(2 if a == 1 else 1, stepsPerUnit / -4)
                    x = x - 1
                    	

#Get L1, L2 based for the point x, y
def getL1L2(x, y, c):
	return math.sqrt((x*x) + (y*y)), math.sqrt( ((c-x)*(c-x)) + (y*y))


#---------------------------------------------------
#Returns delta of L1, and L2
def moveTo(x, y, newX, newY, c):
	global gearRadius, stepsPerRev
	currL1, currL2 = getL1L2(x, y, c)
	newL1, newL2 = getL1L2(newX, newY, c)
	
	steps1 = numberOfSteps(newL1 - currL1, gearRadius, stepsPerRev)
	steps2 = numberOfSteps(newL2 - currL2, gearRadius, stepsPerRev)
	#the direction 
	dir1 = steps1 / abs(steps1) if steps1 != 0.0 else 1.0
	dir2 = steps2 / abs(steps2) if steps2 != 0.0 else 1.0

	print " **from: (",x, y, ") to ( ", newX, newY, ") steps Motor 1:", dir1, steps1, " steps Motor 2:", dir2, steps2

	steps1 = abs(steps1)
	steps2 = abs(steps2)
	
	if isRpi:
            for a in range(0, (int(round(max(steps1, steps2))))):                    
                if steps1 > 0:  
#       	    	print "spinning motor1 steps remaining:", steps1
           	    moveSteps(1, dir1, True)
		    steps1 = steps1 - 1

                if steps2 > 0:
#	        	print "spinning motor2 steps remaining", steps2
                    moveSteps(2, dir2, True)
		    steps2 = steps2 - 1

		if steps1 > steps2 and steps1 > 0 and steps2 > 0:
		    s = math.floor(steps1 / steps2)
		    moveSteps(1, s*dir1, True)
		    steps1 = steps1 - s
    		    print " *m1 steps remaining:", steps1, " added:", s
		elif steps2 > steps1 and steps1 > 0 and steps2 > 0:
		    s = math.floor(steps2/ steps1)
		    moveSteps(2, s*dir2, True)
		    steps2 = steps2 - s
       		    print " *m2 steps remaining:", steps2, " added:", s

        return newX, newY

#---------------------------------------------------
if isRpi:
	def setStep1(w1, w2, w3, w4):
		GPIO.output(motor1_A_1_pin, w1)
		GPIO.output(motor1_B_1_pin, w2)
		GPIO.output(motor1_A_2_pin, w3)
		GPIO.output(motor1_B_2_pin, w4)

#Find number of steps to move arc L
def numberOfSteps(L, gearRadius, stepsPerRev):
	deg = (360.0 * L) / (math.pi * gearRadius)
	print "  degrees to rotate: ", deg
	return deg / (360.0 / stepsPerRev)

def findRadius(L, stepsPerRev, steps):
	return (L * 180.0) / (math.pi * (360.0 * steps / stepsPerRev))

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

