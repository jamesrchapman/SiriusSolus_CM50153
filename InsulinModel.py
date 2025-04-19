
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
class Muscle:
  def __init__(self, organism):
    # Has a Glycogen Reservoir
    pass
# 4. Muscle Breakdown (Catabolism for Gluconeogenesis)

# Role: Provides amino acids to liver for gluconeogenesis.

# Triggers: Cortisol, severe fasting, insulin deficiency.

# Effect: Indirectly raises glucose; slow, maladaptive.

# 5. Muscle (via GLUT-4)

# Role: Major site of glucose uptake and storage as glycogen.

# Triggers: Insulin, exercise.

# Dynamics:

# Insulin-mediated uptake via GLUT-4 translocation.

# Exercise-mediated uptake independent of insulin (AMPK pathway).

# Ketogenesis 
#   No glucose produced here, but reduces brain glucose need and can indirectly reduce hepatic glucose output demand. 
#   Trigger (low insulin, high glucagon, prolonged fasting or carb restriction This is like step one of hepatic gluconeogenesis)
  
# Muscle Glycogenolysis
#   Generally doesn't increase blood glucose because use is local, but it lowers demand (at least until you run out of glycogen)
# (conversely, glycogenesis - insulin mediated - exercise induced increase of insulin sensitivity

# Muscle lacks Glucose 6 Phosphatase so it can't put glucose in the blood!

# Effect: Rapid uptake within 10–30 min after insulin; also drops glucose during activity.

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class Adipose:
  def __init__(self, organism):
    self.organism = organism
    
"""
6. Adipose Tissue

Role: Uptakes glucose for fat synthesis and storage.

Triggers: Insulin.

Effect: Mild-to-moderate effect on glucose, dependent on nutritional state.


Ketogenesis 
  No glucose produced here, but reduces brain glucose need and can indirectly reduce hepatic glucose output demand. 
  Trigger (low insulin, high glucagon, prolonged fasting or carb restriction This is like step one of hepatic gluconeogenesis)


Leptin producer
as leptin gets lower the HPA freaks out and says we need more energy, we gotta eat

"""

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
class Brain:
  def __init__(self, organism):
    self.organism = organism
"""
7. Brain

Role: Constant glucose consumer, not insulin-dependent.

Triggers: Continuous need.

Dynamics: Uses glucose at ~5 mg/kg/min in dogs; steady but can't modulate based on availability.

Effect: Background sink, ~20% of daily glucose.
"""

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class IIT: #Insulin independent tissues including RBCs
  def __init__(self, organism):
    self.organism = organism
"""
9. Red Blood Cells & Other Insulin-Independent Tissues

Role: Baseline uptake.

Effect: Minor constant drain.

"""
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
"""

Ways Glucose is produced:



Renal Gluconeogenesis
  Like a smaller 15% version of the liver's gluconeogenesis
    Triggers?






"""

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class Hydration:
  def __init__(self, organism):
    self.organism=organism
  # Dehydration can concentrate glucose and reduce perfusion.
  # Affects kidney function and insulin distribution.
  pass

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class Liver:
  def __init__(self,organism):
    pass
# 1. Liver

# Role: Glucose production via glycogenolysis and gluconeogenesis.

# Triggers:

# Low blood glucose (absolute and slope).

# Hormones: cortisol, glucagon, epinephrine.

# Fasting state or circadian rhythm (e.g. dawn phenomenon).


# Dynamics: PID-like—responds to level (P), rate of change (D), and sometimes anticipatory meal patterns (I-like).

# Limits: Finite glycogen stores (~12–18h fasting reserve in dogs).

# Effect: Rapid (minutes), peaking within 15–60 mins.
# Hepatic Glycogenolysis
#   Very Fast (Minutes)
#     Triggered by glucagon, epi, cortisol, low insulin
#     Stimulated by Cytokines (Inflammation)
# Hepatic Gluconeogenesis
#   breaking down metabolic byproducts (protein breakdown, fat breakdown, lactate - yielded up by cori cycle, ketogenesis, alanine cycle, whatever)
#     Triggered by Glucagon, Cortisol, Low Insulin, Growth Hormone, strongly upregulated by inflammation (e.g. cortisol, cytokines)
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class Pancreas:
  def __init__(self,organism):
    pass
# glucagon, insulin, somatostatin
# Sympathetic inhibition of insulin
# Beta cells (insulin) inhibit alpha cells (glucagon)

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
    
class Kidneys:
  def __init__(self,organism):
    pass
# 3. Kidney (Gluconeogenesis in Cortex)

# Role: Produces small amounts of glucose during prolonged fasting.

# Triggers: Low insulin, high cortisol.

# Effect: Minor contributor, ~10% of total gluconeogenesis.
"""
8. Kidneys (Filtration & Glucosuria)

Role: Filter glucose; excrete it if over renal threshold (~180–200 mg/dL in dogs).

Effect: Passive safety valve; if glucose is high, spill it into urine → mild glucose lowering.
"""

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class Intestine:
  def __init__(self,organism):
    self.organism=organism

# 2. Intestines (Duodenum, Jejunum)

# Role: Absorb glucose from digested food.

# Triggers: Food arrival.

# Dynamics: Slow onset (starts ~15–30 mins), peaks ~60–90 mins, can last 3+ hours depending on food type.

# Effect: Major post-prandial source. Fat and fiber slow absorption.

# Digestion
#   Carbohydrate
#     Complex (60-180 minutes)
#     Simple (15-30 minutes)

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class Activity(self,organism): # maybe just put this in muscle
  pass

# 18. Exercise / Movement

# Muscle glucose uptake increases independent of insulin.

# Effect can last hours after intense activity.

# Also enhances insulin sensitivity.

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class CGM:
  def __init__(self, organism):
    pass

# 17. Glucose Monitors (Libre etc)

# Measure interstitial glucose, delayed ~10–15 min from blood.

# Sensitive to noise, compression, temperature.
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
class Exogenous_Insulin:
  pass
  
  # 16. Exogenous Insulin
  
  # Vetsulin, NPH, Detemir, Glargine, Regular, etc.
  
  # Delivered subq, lagging effect, varies by formulation.
  
  # Mimics or replaces pancreatic insulin.

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  

class Canine:
  def __init__(self, initial_bgl = 200):
    self.hydration = Hydration(self)
    self.BGL = initial_bgl
    self.cortisol
    """
        
    12. Cortisol
    
    Role: Mobilizes energy for stress; promotes gluconeogenesis.
    
    Triggers: Stress, circadian rhythm (high in early morning).
    
    Dynamics: Slow (~30–90 min delay), long-lasting.
    
    Effects:
    
    Stimulates liver + kidney glucose production.
    
    Promotes insulin resistance.
    
    Encourages protein catabolism → amino acids for gluconeogenesis.

    """
    self.cytokines
    """
    


    19. Inflammation / Illness / Infection
    
    Cytokines (like TNF-α, IL-6) can cause insulin resistance.
    
    Fever raises basal metabolic rate and glucose production.
    """
    self.incretins
        
    # 15. Incretins (GLP-1, GIP)
    
    # Role: Gut-derived hormones that stimulate insulin after eating.
    
    # Effect:
    
    # Boost insulin release.
    
    # Slightly inhibit glucagon.
    
    # Delay gastric emptying → slow glucose rise.
    self.insulin
    """
    10. Insulin

    Role: Master controller of uptake and storage.
    
    Triggers: High glucose, gut hormones (GLP-1).
    
    Dynamics: Rapid secretion after meals; synthetic subq onset ~15–60 mins.
    
    Effects:
    
    Increases GLUT-4 activity.
    
    Inhibits liver glucose production.
    
    Promotes fat/muscle glucose storage.
    """
    self.glucagon
    """
    pancreas production - low BGL (Main trigger)
    High protein intake can stimulate glucagon
    Exercise ( more specific maybe? )
    Epi
    Cortisol

    Suppressed by
    High BGL
    Local Insulin Production (paracrine inhibition)
    somatostatin
    incretin
    """
    self.epinephrine
    """
        13. Epinephrine (Adrenaline)
    
    Role: Rapid stress response.
    
    Triggers: Fear, pain, fight/flight.
    
    Effects:
    
    Liver glucose dump.
    
    Inhibits insulin secretion.
    
    Stimulates lipolysis (energy mobilization).
    
    Vasoconstriction (affects perfusion/glucose distribution).
    """
    self.somatostatin
    self.growth_hormone
    
    
    # 14. Growth Hormone
    
    # Role: Increases insulin resistance, especially in fat.
    
    # Triggers: Sleep, puberty, stress.
    
    # Effect: Mild contributor to glucose elevation in chronic cases.



    

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  
    
