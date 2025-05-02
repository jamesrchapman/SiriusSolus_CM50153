from scipy.stats import gamma
import numpy as np
import matplotlib.pyplot as plt

# k = 2.0  # shape
# theta = 2.0  # scale

# import numpy as np
# x = np.linspace(0, 20, 1000)
# y = gamma.pdf(x, a=k, scale=theta)

# plt.plot(x, y)
# plt.show()


def gamma_kernel(t, onset, k, theta):
    t = np.asarray(t)  # make sure t is an array even if a scalar
    effect = np.where(
        t < onset,
        0,
        gamma.pdf(t - onset, a=k, scale=theta)
    )
    return effect


DOSE_RANGE = [0.0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.20, 0.25]

# good ideas for state vector - bgl, bgl rate, time of day/cycle)

class Canine:
	def __init__(self, BGL = 250, step_size = 5, time = 24*60*500):
		# 250mg/dl, 5 minute intervals, run for a day,
		self.step_size = step_size
		self.time = np.linspace(0, time, 24*60//5)
		self.BGL = np.zeros_like(self.time)
		self.BGL[0] = BGL
		self.BGL_Rate = np.zeros_like(self.time)
		self.constant_background_use_rate = 0 # Brain and stuff that uses glucose straight up
		self.kidney_clearance_rate = 2/20/1000 # 
		# suppose dogs have a GFR (mL/min/kg) of about 2 (people are around 1.8, dogs are a bit faster)
		# should divide by 10 for plasma to blood ratio
		# multiply by bodyweight in kg
		# so for benny let's guess - 2*10/10 = 2
		# then there's only about 1/10 or 1/20 of the glucose that leaks out of the kidneys (that's a rough estimate)
		# and you gotta do a dl to ml conversion, which is like 100
		self.effective_insulin = np.zeros_like(self.time)
		self.insulin_contributions = dict()
		self.insulin_sensitivity = 0.62 #several things wrapped up in here, but probably just a scalar for dose 
		# reminder that peak is at about (k-1)*theta
		self.insulin_curve_k = 4.0 # complexity of absorption process
		self.insulin_curve_theta = 70.0 # average rate of insulin absorption processes
		self.food_curve_k = 8.0 # complexity of absorption process
		self.food_curve_theta = 10.0 # average rate of insulin absorption processes
		self.food_sensitivity = 8.0 # has something to do with size and digestion efficiency
		self.effective_food = np.zeros_like(self.time)
		self.insulin_doses = dict() # index_time -> dose
		self.food_doses = dict() # index_time -> dose


	def dose_insulin(self, administration_time, units):
		insulin_dose = lambda t: units * (gamma_kernel(t, onset = administration_time, k= 3 , theta = 105) 
			+ gamma_kernel(t, onset = administration_time, k=5, theta = 120))
		self.insulin_contributions[administration_time] = insulin_dose
		self.effective_insulin += insulin_dose(self.time)
		# Could be altered by exercise



	def dose_food(self, administration_time, units):
		# time in minutes, units in calories
		food_dose = lambda t: self.food_sensitivity * units * ( gamma_kernel(t, onset = administration_time, k=4, theta= 22) 
			+ gamma_kernel(t, onset = administration_time, k=7, theta=24)
			)
		self.effective_food += food_dose(self.time)

	def update(self, index):
		if index == 0:
			pass
		else:

			self.BGL[index] = (
				self.BGL[index -1]
				+ self.effective_food[index-1]
				- self.step_size * self.BGL[index-1] * self.insulin_sensitivity * self.effective_insulin[index-1]
				- self.step_size * self.constant_background_use_rate
				- self.step_size * self.kidney_clearance_rate * max(0, self.BGL[index-1]-180)
				)
		pass


# G'(t) = a_1 \, \Gamma_1(t) - a_2 \, \Gamma_2(t) \times G(t) - a_3 - a_4 \, \max(0, G(t)-180) + \epsilon(t)

# So pretty much this. 
# Where:

# a_1 = food scaling

# a_2 = insulin strength scaling

# a_3 = constant background use

# a_4 = kidney clearance rate

# Epsilon = positive noise (cortisol) 


	def run(self):
		index = 0
		while index < len(self.time):
			self.update(index)
			index +=1
		print('finished')

	def plot_bgl(self):
		plt.plot(self.time,self.BGL)

		plt.xlabel('Time')
		plt.ylabel('BGL (mg/dl)')
		plt.title('Glucose Curve')
		plt.grid(True)
		plt.show()

	def plot_insulin(self):
		plt.plot(self.time,self.effective_insulin)
		plt.xlabel('Time ')
		plt.ylabel('insulin?')
		plt.title('Insulin Curve')
		plt.grid(True)
		plt.show()

	def plot_food(self):
		plt.plot(self.time, self.effective_food)
		plt.xlabel('Time ')
		plt.ylabel('food')
		plt.title('Food Curve')
		plt.grid(True)
		plt.show()

def bin_glucose(g):
    if g < 60:
        return 0
    elif g < 80:
        return 1
    elif g < 130:
        return 2
    elif g < 200:
        return 3
    elif g < 300:
        return 4
    elif g < 400:
        return 5
    else:
        return 6

def bin_glucose_rate(g):
    if g < -3:
        return 0
    elif g < -1.5:
        return 1
    elif g < -0.5:
        return 2
    elif g < 0.5:
        return 3
    elif g < 1.5:
        return 4
    elif g < 3:
        return 5
    else:
        return 6

def bin_iob(i):
	if i < 0.0025:
        return 0
    elif i < 0.005:
        return 1
    elif i < 0.0075:
        return 2
    elif i < 0.010:
        return 3
    elif i < 0.0175:
        return 4
    elif i < 0.0250:
        return 5
    else:
        return 6

def bin_fob(i):
	if i < 2.5:
        return 0
    elif i < 5.0:
        return 1
    elif i < 7.5:
        return 2
    elif i < 10.0:
        return 3
    elif i < 15.0:
        return 4
    elif i < 20.0:
        return 5
    else:
        return 6

from dataclasses import dataclass

@dataclass
class Welford:
    n: float = 0.0
    mean: float = 0.0
    M2: float = 0.0
    def update(self, value: float, weight: float = 1.0):
        self.n += weight
        delta = value - self.mean
        self.mean += (weight / self.n) * delta
        delta2 = value - self.mean
        self.M2 += weight * delta * delta2
    def variance(self):
        return self.M2 / self.n if self.n > 0 else 0.0
    def stddev(self):
        return self.variance() ** 0.5
    def count(self):
        return self.n
    def reset(self):
        self.n = 0.0
        self.mean = 0.0
        self.M2 = 0.0
    def ucb1(self, total_trials: float, c: float = 1.0):
        if self.n == 0:
            return float('inf')
        return self.mean + c * math.sqrt(math.log(self.n) / self.n)

class Pump:
	def __init__(self,canine):
		self.canine = canine
		self.qtable = defaultdict(defaultdict(Welford)) # [bgl, bgl_rate, iob, fob][dose] -> Welford(n,reward_average,running sum of squares of differences from the mean)
	def get_key(self,index):
		key=(self.canine.bgl[index],self.canine.bgl_rate[index],self.canine.iob[index],self.canine.fob[index])
		# Gotta bin the key
		return key
	def get_dose(self,index):
		self.canine.insulin_doses[index]
	def train_dosing_scheme(self):
		index = 0
		while index < len(self.canine.time):
			self.canine.update(index)
			self.adjust_table(index) # reward / punish table
			insulin_dose = self.choose_dose(index)
			self.canine.dose_insulin(index,insulin_dose)
			index+=1
	def bgl_penalty(self,index):
	    if 90 <= self.canine.bgl[index] <= 130:
	        return 0
	    elif self.canine.bgl[index] < 90:
	        return 0.05 * ((90 - self.canine.bgl[index]) ** 2)  # steeper penalty for low BGL
	    else:
	        return 0.0005 * ((self.canine.bgl[index] - 130) ** 2)
	def choose_dose(self,index):
		key = self.get_key(index)
		dose_to_use = DOSE_RANGE[0]
		for dose in DOSE_RANGE:
			if self.qtable[key][dose].ucb1
			self.qtable[key][dose] for dose in DOSE_RANGE
		pass 
		# we can run 
	def update_reward(self,index,weight,reward):
		key = self.get_key(index)
		dose = self.get_dose(index)
		self.qtable[key][dose].update(reward,weight)
	def adjust_table(self,index):
		responsibility = self.canine.insulin_contributions[:][index]/self.canine.effective_insulin[index]
		for dose_idx, weight in responsibility:
			self.update_reward(dose_idx, weight, self.bgl_penalty)
		pass 
		# maybe we should account for a sense of "what the dose should have been" e.g. if bgl is high, don't punish a high insulin dose as much as a low dose. But I'm gonna skip it









def main():
	start = 0 # hours
	cycle = 12 #hours
	num_cycles = 1
	print('good luck!')
	Benny = Canine(BGL=370,time = cycle*60*num_cycles)
	for t in range(start, 720000, cycle*60):
   		Benny.dose_food(t, 150)


	Benny.dose_insulin(1, 5.0)
	Benny.dose_food(90, 130)
	Benny.dose_insulin(60*8, 5.0)
	Benny.dose_food(60*8+90, 130)
	Benny.dose_insulin(60*16, 5)
	Benny.dose_food(60*16+90, 130)

	Benny.run()
	Benny.plot_bgl()
	Benny.plot_insulin()
	Benny.plot_food()


if __name__ == '__main__':
	main()








"""



Glucose at time t -> G(t)
Sensitivity to Insulin -> SI
nI -> insulin clearance rate
F-> bioavailability like 1.0 for subq 
Clearance rate = (Dose × F) / AUC
Ib -> basal insulin concentration 
G(t)=G(t-s)+s(food rate in - SI*I(t-s)*G(t-s)-kidneys-brain+glycolysis+gluconeogenesis)
Brain is pretty constant
Kidneys are probably glucose proportional above 180 -> (G-180) for G>180, 0 otherwise. 
Glycolysis and gluconeogenesis are pretty hard to predict for now. 
(G(t)-G(t-s))/s= food rate in - SI*I(t-s)*G(t-s)-kidneys-brain+glycolysis+gluconeogenesis


dI/dt = -nI * (I - Ib)


Eh. I guess it's like, I have some rate of absorption proportional to the amount not yet absorbed, and then
So...
B(0)=B_0 B'=-k_b×B And then A'=-B'-k_a×A
Right? That's probably soluble.

A(t) = \frac{k_b B_0}{k_a - k_b} \left( e^{-k_b t} - e^{-k_a t} \right)

That's probably the right shape for the insulin kernel but I don't know what the constants are. 


And then say food rate is a sigmoid sorta curve with a peak near 90 minutes but just call it food peak, and it will be roughly proportional to the food bolus

Oh good news I just derived the property of biological systems that indicates that drug absorption generally follows a gamma curve that's because it's the convolution of a bunch of exponential processes eg1 process decays into another process which decays into another process which decays into another process and on and on and on creates the gamma obviously it's not immediately a gamma but you know it's pretty close. 

A(t) = K \cdot t^{k-1} e^{-t/\theta}

Okay so we know glucose all the time. 
And then we know that the food concentration kernel should be the same and proportional to the meal size say in calories and we know when that is administered. 
And the same goes for the insulin kernel. 
So the goal here is to back calculate the insulin concentration/effect kernel and the food concentration kernel. 


So we just wanna know those kernels. 

I think we also need to take into account like the rate of say gluconeogenesis and glycolysis. But the thing is I'm going to have a pretty hard time guessing what those are and I don't have any data on that so maybe it'll just be background noise for us. 

And then a priori, we have a hunch that the insulin kernel should peak around like 3 and 1/2 hours and follows that differential equation that we have. At least sort of, but I think that's more just like exponential decay which is sort of obvious. And then the rate at which it approaches peak I don't know if I really care and maybe we can just look up what that should look like. 

The food bolus is pretty weird and I don't really know what it would look like but I do think it probably peaks around an hour and a half and I think is mostly done after 3 hours but I don't know. And I don't really think that follows an exponential decay but I would be happy to be shown to be wrong... Digestion seems to be more of a specific process with a specific kind of curve shape I think it might be delayed a bit depending on the size of the meal but I don't know. 
Also sometimes I probably make it hard to determine because my administration is spread out which you know is probably you know easier on his digestion at least but it makes it harder to predict. 


Then the other factors I think are primarily glycolysis and gluconeogenesis oh and kidneys. The kidney filtration rate is probably something that's studied and maybe we can steal a differential equation or something. 

I know that there are some other things at play here like the body will uptake glucose at some rate as well just to use like your brain or some other things I can't remember. I'm not sure what percent that is or what it would look like but that's another factor to consider but I think that's just a base rate. 

I'm willing to bet that the kidney filtration is like what like proportional to the glucose above like 200 mg per deciliter or maybe it's 180 I can't remember. And maybe something else like hydration right but I don't even know. It's probably complicated. But I bet that's close. 

The liver deciding to do glycolysis is not completely unpredictable but a little bit you know it's one of the more complicated parts and it's not entirely obvious that it's perfectly mathematical. 
Same goes for gluconeogenesis, I'm going to have a pretty hard time predicting serum cortisol, and even if I did I think it's still hard to determine the rate of gluconeogenesis. But I think we can work with base use of glucose without insulin the rate at which insulin causes glucose to be taken up maybe even factoring in glut4 and exercise, kidneys, , and digestion. And you know the other stuff we'll just have to say is like stress or glycolysis and it's sort of out of our control, through the use of the pump we could potentially you know put out fires and cope with that rise better especially if we were able to name it and say oh okay that's not food that's you know glycolysis that's gluconeogenesis because Benny's probably stressed right... 

So yeah right now the goal is just I guess make a good go of finding a food kernel and a insulin kernel. 

So I think the first thing to do is write up our really nasty system of equations, call some of them futile to solve for, and then look at I think the difference equation which we can solve for based on glucose curves and then try inserting different food and insulin kernels and see how bad they predict the data I guess. 
Yeah I guess that basically makes sense. And then we'd also want to factor in like kidney filtration rate and base glucose use (brain et al) 

Oh and then there's the pathological state of hyperglycemia induced cortisol -_- which is a big oh boy, and I wouldn't know how to predict that or account for it. 
And pancreatitis flare-ups P
And illness
And anything cortisol -_-
But let's just ignore that for now and call the noise stress. 


G'(t) = a_1 \, \Gamma_1(t) - a_2 \, \Gamma_2(t) \times G(t) - a_3 - a_4 \, \max(0, G(t)-180) + \epsilon(t)

So pretty much this. 
Where:

a_1 = food scaling

a_2 = insulin strength scaling

a_3 = constant background use

a_4 = kidney clearance rate

Epsilon = positive noise (cortisol) 


Also note that food and insulin may both be better modeled by gamma mixture models 


"""



