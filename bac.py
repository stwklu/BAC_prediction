#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import sys

class BAC(object):
	'''
	This is our main model
	'''
	def __init__(self, args):
		#print(args["elimination_rate"])
		self.args = args
		# initial alcohol concentration (gram)
		self.alcohol_con = self.args["init_alc"]

		# compute fluid amount
		self.weight = self.args["weight"] / 2.2046 # in kg
		if self.args["gender"] == 1:
			self.fluid = 0.68 * self.args["weight"]
		else:
			self.fluid = 0.65 * self.args["weight"]

		# initial BAC level
		self.alcohol_level = self.alcohol_con / self.fluid

		# discrete time model
		self.t = 0 # time step
		self.peakTime = 0
		self.peakCon = self.alcohol_level
		self.sober = None
		self.legal = None
		self.finish_drink = None

		# Set params for continuous model
		if self.args["model"] == "continuous":
			self.elim_rate = 0.2 * 1.1
			self.cons_rate = self.args["consumption"]["rate"]
			#print(self.cons_rate)
			self.to_be_absorb = 0#self.args["consumption"]["total"]
			self.con_histroy = 0

	# progressive consumption of alcohol
	def absorb(self):
		#if self.args["model"]=="discrete" and \
		if self.args["consumption"]["model"] == "linear" and \
		self.t <= self.args["consumption"]["step"]:
			self.alcohol_con += self.args["consumption"]["rate"]
			self.alcohol_level = self.alcohol_con / self.fluid
		if self.args["consumption"]["model"] == "absorbtion":
			self.to_be_absorb += self.args["consumption"]["rate"]
			self.alcohol_con += min(self.cons_rate, self.to_be_absorb)
			self.alcohol_level = self.alcohol_con / self.fluid
			self.to_be_absorb -= min(self.cons_rate, self.to_be_absorb)
			#print(self.to_be_absorb)

	# progressive eliminaion of alcohol
	def eliminate(self):
		if self.args["model"]=="discrete" \
		and self.args["consumption"]["model"] == "linear":
			self.alcohol_con -= self.args["elimination_rate"]
			self.alcohol_level = self.alcohol_con / self.fluid

		if self.args["model"]=="continuous":
			if self.con_histroy <= self.args["consumption"]["total"]:
				self.finish_drink = self.t
				self.con_histroy += (self.elim_rate+self.cons_rate)*self.alcohol_con
				self.alcohol_con = (1-self.elim_rate+self.cons_rate)*self.alcohol_con
				self.alcohol_level = self.alcohol_con / self.fluid
			else:
				self.alcohol_con = (1-self.elim_rate)*self.alcohol_con
				self.alcohol_level = self.alcohol_con / self.fluid


	# making one time step for discrete model
	def step(self):
		#self.absorb()
		if self.alcohol_level > 0:
			self.eliminate()
		else:
			self.alcohol_con = 0
			self.alcohol_level = 0
		self.t += 1

		if self.alcohol_level > self.peakCon:
			self.peakCon = self.alcohol_level
			self.peakTime = self.t
		if not self.sober:
			if abs(self.alcohol_level) < 0.0001:
				self.sober = self.t
		if not self.legal:
			if self.alcohol_level <= 0.08:
				self.legal = self.t
		if self.alcohol_level >= 0.08:
			self.legal = None

	# output bac and alcohol level
	#	- timestep parameter only valid for continuous model
	def output(self, timestep=100, single_shot=False):
		if single_shot == False:
			return max(self.alcohol_con, 0), max(self.alcohol_level,0)
		elif self.args["model"] == "continuous" and single_shot == True:
			if self.args["consumption"]["rate"] == 0:
				# average percentage consumption
				self.alcohol_level = self.alcohol_level * np.exp(self.elim_rate * timestep)
			else:
				print("Invalid...")

	def getPeak(self):
		return self.peakTime, self.peakCon

	def getSoberTime(self):
		return self.sober

	def getLegalDriveTime(self):
		return self.legal

def scatter_plot(args, num_trial = 100, total_time=500):

	all_trial = [None]*num_trial
	rate_all = np.zeros(num_trial)
	total_all = np.zeros(num_trial)
	peakTime_all = np.zeros(num_trial)
	peakCon_all = np.zeros(num_trial)
	sober_all = np.zeros(num_trial)
	legal_all = np.zeros(num_trial)

	for i in range(num_trial):
		rate_all[i] = np.random.normal(0.3, 0.03)
		total_all[i] = np.random.normal(68, 6.8)
		args["consumption"]["rate"] = rate_all[i]
		args["consumption"]["total"] = total_all[i]
		all_trial[i] = BAC(args)

	for i in range(num_trial):
		for t in range(total_time):
			all_trial[i].step()
		peakTime_all[i], peakCon_all[i] = all_trial[i].getPeak()
		sober_all[i] = all_trial[i].getSoberTime()
		legal_all[i] = all_trial[i].getLegalDriveTime()

	# Draw 3d graph
	fig = plt.figure()
	# peak BAC
	ax = fig.add_subplot(221, projection="3d")
	ax.scatter(rate_all, total_all, peakCon_all)
	ax.set_xlabel('absorption rate (I)')
	ax.set_ylabel('Total alcohol consumption')
	ax.set_zlabel('Peak BAC level')

	# Peak BAC time
	ax = fig.add_subplot(222, projection="3d")
	ax.scatter(rate_all, total_all, peakTime_all)
	ax.set_xlabel('absorption rate (I)')
	ax.set_ylabel('Total alcohol consumption')
	ax.set_zlabel('Peak BAC time')

	# sober time
	ax = fig.add_subplot(223, projection="3d")
	ax.scatter(rate_all, total_all, sober_all)
	ax.set_xlabel('absorption rate (I)')
	ax.set_ylabel('Total alcohol consumption')
	ax.set_zlabel('sober time')

	# legal to drive time
	ax = fig.add_subplot(224, projection="3d")
	ax.scatter(rate_all, total_all, legal_all)
	ax.set_xlabel('absorption rate (I)')
	ax.set_ylabel('Total alcohol consumption')
	ax.set_zlabel('time until legal to drive')

	plt.show()

def continuous_example(args, total_time=500):
	bac_discrete = BAC(args)
	concentrations_contiuous = np.zeros(total_time)
	bac_level_continuous = np.zeros(total_time)

	# continuous model
	args["model"] = "continuous"
	bac_continuous = BAC(args)

	for i in range(total_time):
		bac_continuous.step()
		c, b = bac_continuous.output()
		concentrations_contiuous[i] = c
		bac_level_continuous[i] = b

	# Plot the result
	plt.plot(bac_level_continuous)
	plt.plot(np.ones(total_time)*0.08)
	plt.plot(np.ones(total_time)*0.35)
	plt.plot(np.ones(total_time)*0.5)
	plt.legend(["Individual BAC level", "legal for driving", "coma", "death"])
	plt.xlabel("Time (minutes)")
	plt.ylabel("BAC")
	plt.show()

	# get value of interest
	peakTime, peakCon = bac_continuous.getPeak()
	legal = bac_continuous.getLegalDriveTime()
	sober = bac_continuous.getSoberTime()
	print("time reaching peak BAC: ", peakTime)
	print("peak BAC: ", peakCon)
	print("legal to drive time: ", legal)
	print("sober time: ", sober)
	print("lamda (stop drinking time): ", bac_continuous.finish_drink)

def discrete_example(args, total_time=500):
	concentrations_discrete = np.zeros(total_time)
	bac_level_discrete = np.zeros(total_time)

	# continuous model
	args["model"] = "discrete"
	bac_discrete = BAC(args)

	# Execute time steps for discrete model
	for i in range(total_time):
		bac_discrete.step()
		c, b = bac_discrete.output()
		concentrations_discrete[i] = c
		bac_level_discrete[i] = b


	# Plot the result
	plt.plot(bac_level_discrete)
	plt.plot(np.ones(total_time)*0.08)
	plt.plot(np.ones(total_time)*0.35)
	plt.plot(np.ones(total_time)*0.5)
	plt.legend(["Individual BAC level", "legal for driving", "coma", "death"])
	plt.xlabel("Time (minutes)")
	plt.ylabel("BAC")
	plt.show()

	# get value of interest
	peakTime, peakCon = bac_discrete.getPeak()
	legal = bac_discrete.getLegalDriveTime()
	sober = bac_discrete.getSoberTime()
	print("time reaching peak BAC: ", peakTime)
	print("peak BAC: ", peakCon)
	print("legal to drive time: ", legal)
	print("sober time: ", sober)
	print("lamda (stop drinking time): ", bac_discrete.finish_drink)

def main():
	# Initial alcohol amount
	num = 6 		# number of drinks
	gram = 13.6 	# grams of alcohol per drink
	init_alc = num * gram

	more_alc = num * gram * 2

	# Model parameter
	args = {
		"elimination_rate" : (float(12)/60) * 1.10, # grams per minute
		"gender" : 0, # 1 for female, 0 for male
		"weight" : 170, # in pound
		"init_alc" : 13.6, # Initial alcohol consumption (grams)
		"model" : "discrete", # model type: "discrete", "continuous"

		# use this for discrete model
		#"consumption" : {"model":"linear", "rate":0.0, "step":0}, # progressive consumming alcohol for discrete model

		# use this for continuous model
		"consumption" : {"model":"absorbtion", "rate":0.3, "total":num*gram-13.6}, # progressive consumming alcohol for continuous model
	}

	total_time = 500
	
	if len(sys.argv) == 1:
		# Example discrete model
		discrete_example(args)
		# Example continuous model
		continuous_example(args)
		# Obtain the scatter plot as in figure 1
		scatter_plot(args, num_trial=100, total_time=total_time)

	elif sys.argv[1] == "discrete":
		discrete_example(args)
	elif sys.argv[1] == "continuous":
		continuous_example(args)
	elif sys.argv[1] == "scatter":
		scatter_plot(args, num_trial=100, total_time=total_time)
	else:
		print("Usage:")
		print("To execute discrete example: ./bac.py discrete")
		print("To execute continuous example: ./bac.py continuous")
		print("To reproduce the scatter plots figure 1: ./bac.py scatter")
	

	return

if __name__ == '__main__':
	main()