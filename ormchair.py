'''
Created on 24 Jan 2013

@author: will
'''
import requests
import uuid
import json

"""
Used for schema validation errors
"""
class ValidationError(Exception):
	def __init__(self, message):
		Exception.__init__(self, message)


"""
Represents an abstract property of a class
"""
class Property(object):
	
	# Stores the actual value of the property
	def __init__(self,*args,**kwargs):
		
		self._name = None
		self._required = kwargs.pop('required', None)
		self._default = kwargs.pop('default', None)
		
	def __get__(self, instance, owner):
		
		if instance is None:
			return self
		else:
			# Has it been previously set?
			if self._name in instance._propertyValues:
				return instance._propertyValues[self._name]
			else:
				return None
	
	def __set__(self, instance, value):
		
		if instance:
			
			if self._validate(value):
				instance._propertyValues[self._name] = value
				instance.setUpdated()
	
	# Set the name of the property
	def setName(self,name):
		
		self._name = name
		
	# Override	
	def _validate(self,value):
		
		return True
	
	# Ovveride
	def toDict(self,instance):
		
		return self.__get__(instance, None)
	
	# Return the default value
	def getDefaultValue(self):
		
		if hasattr(self,"_default"):
			return self._default
		else:
			return None

""" 
Metaclass to set the name on the descriptor property objects
"""
class PropertyDescriptorResolverMetaClass(type):
	
	def __new__(cls, classname, bases, classDict):
		
		# Store a static variable of the property names
		classDict["_properties"] = []
		for base in bases:
			if hasattr(base,"_properties"):
				classDict["_properties"].extend(base._properties)

		# Iterate through the new class' __dict__ and update all recognised property names
		for name, attr in classDict.iteritems():
			
			if isinstance(attr, Property):
				
				# Store the name of the property in the descriptor
				attr.setName(name)
				
				# Append the name of the property to class var
				classDict["_properties"].append(name)
				
		return type.__new__(cls, classname, bases, classDict)

"""
Mapped to a class
"""
class Schema(object):
	
	# Set the name on all the descriptors within this class
	__metaclass__ = PropertyDescriptorResolverMetaClass
	
	def __init__(self,*args,**kwargs):
		
		# Defaults
		self._type = "object"
		self._required = []
		
		# Used to store actual values of properties (can't store in descriptor objects as they are static)
		self._propertyValues = {}
		
		# Stores whether this object has had properties changed
		self._updated = False
		
		# Set parent and defaults on properties
		for property_name in self._properties:
			
			# Defaults
			default_value = getattr(self.__class__,property_name).getDefaultValue()
			setattr(self,property_name,default_value)
	
	# Set the values of the schema from a dict	
	def fromDict(self,dict_data):
		if isinstance(dict_data,dict):
			for key in dict_data:
				if key in self._properties:
					setattr(self,key,dict_data[key])
				else:
					raise ValidationError("No property %s exists" % key)
	
	# Export the schema as a basic dict
	def toDict(self):
		
		dict_data = {}
		
		# Loop over properties
		for property_name in self._properties:
			
			dict_data[property_name] = getattr(self.__class__,property_name).toDict(self)
		
		return dict_data	
	
	def setUpdated(self):
		self._updated = True
	

"""
A string property of a class
"""
class StringProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		self._minLength = kwargs.pop('minLength', None)
		self._maxLength = kwargs.pop('maxLength', None)
		
		# Not implemented
		self._format = kwargs.pop('format', None)
		self._pattern = kwargs.pop('pattern', None)
		
		super(StringProperty, self).__init__(self,*args,**kwargs)
		
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, basestring):
			raise ValidationError("Not a string")
		
		# Check minimum length
		if value and self._minLength and len(value) < self._minLength:
			raise ValidationError("String is less than minimum length")
			
		# Check maximum
		if value and self._maxLength and len(value) > self._maxLength:
			raise ValidationError("String is greater than maximum length")
		
		return True

"""
A number property of a class
"""
class NumberProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		self._minimum = kwargs.pop('minimum', None)
		self._maximum = kwargs.pop('maximum', None)
		
		# Not implemented yet
		self.format =kwargs.pop('format', None)
		self.divisibleBy = kwargs.pop('divisibleBy', None)
		
		super(NumberProperty, self).__init__(self,*args,**kwargs)
		
	# Override	
	def _validate(self,value):
		
		# Check type
		if value and not isinstance(value, (int, long, float, complex)):
			raise ValidationError("Not a number")
		
		# Check minimum
		if value and self._minimum and value < self._minimum:
			raise ValidationError("Number is less than minimum")
			
		# Check maximum
		if value and self._maximum and value > self._maximum:
			raise ValidationError("Number is greater than maximum")
			
		return True
		
			

"""
An integer property of a class
"""
class IntegerProperty(NumberProperty):
	
	def __init__(self,*args,**kwargs):
		super(IntegerProperty, self).__init__(self,*args,**kwargs)
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, int):
			raise ValidationError("Not a number")
		
		return True
	

"""
A boolean property of a class
"""
class BooleanProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		# Not implemented
		self._format = kwargs.pop('format', None)
		
		super(BooleanProperty, self).__init__(self,*args,**kwargs)
		
	
	# Override	
	def _validate(self,value):
		
		if value and not isinstance(value, bool):
			raise ValidationError("Not a boolean")
		
		return True


"""
Allows for composite properties
"""
class DictProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		super(DictProperty, self).__init__(self,*args,**kwargs)
		
		# Create a new subclass of Schema
		self._cls = type('SchemaSubClass', (Schema,), kwargs)
		
	def __get__(self, instance, owner):
		
		if instance is None:
			# Return descriptor
			return self
		else:
			self._checkForPropertyValue(instance)

			# Return instanc of subclas
			return instance._propertyValues[self._name]
	

	def __set__(self, instance, value):
		
		self._checkForPropertyValue(instance)
		
		instance._propertyValues[self._name].fromDict(value)
	
	# Make sure property value has been set	
	def _checkForPropertyValue(self,instance):
		# Check to see if property exists on instance
		if self._name not in instance._propertyValues:
				
			# Create instance of schema subclass
			instance._propertyValues[self._name] = self._cls()
	
	def toDict(self,instance):
		
		property_data = {}
		
		# Get the instance of the dict_property subclass
		dict_property_instance = getattr(instance,self._name)
		
		# Loop the properties
		for property_name in dict_property_instance._properties:	
			# Recurse on toDict
			property_data[property_name] = getattr(dict_property_instance.__class__,property_name).toDict(dict_property_instance)
		
		return property_data
	
	def fromDict(self,instance,dict_data):
		
		# Loop the properties
		for property_name in instance._properties:	
			
			# Set the instance value
			setattr(instance,property_name,dict_data[property_name])

# Thanks to http://stackoverflow.com/questions/12201811/subclass-python-list-to-validate-new-items
class DictPropertyList(list):
	
	def __init__(self, itr, cls): 
		
		self._cls = cls
		
		# If a list has been passed in then validate
		if itr == None:
			itr = []
		else:
			itr = map(self._validate, itr)
		
		super(DictPropertyList, self).__init__(itr)

	# Unbound method just stored in class for encapsulation
	def wrap(f, takes_list=False, validate_arg_index=0):
		def wrapped_f(self,*args):
			
			# args is tuple which is immutable
			list_args = list(args)
			
			# Do we need to map each item to validate function?
			if takes_list:
				list_args[validate_arg_index] = map(self._validate, args[validate_arg_index])
			else:
				list_args[validate_arg_index] = self._validate(args[validate_arg_index])
			
			return f(self,*list_args)
		return wrapped_f
	
	# Check value is ok
	def _validate(self, value):
		
		# Create a new instance of Schema subclass
		list_instance = self._cls()
		
		# Populate from dict (and thus validate)
		list_instance.fromDict(value)
		
		return list_instance
	
	# Override all methods that add an item to the list
	append = wrap(list.append)
	extend = wrap(list.extend,takes_list=True)
	insert = wrap(list.insert,validate_arg_index=1)
	__add__ = wrap(list.__add__,takes_list=True)
	__iadd__ = wrap(list.__iadd__,takes_list=True)
	__setitem__ = wrap(list.__setitem__)
	__setslice__ = wrap(list.__setslice__,takes_list=True)		

""" 
Special property that represents an list property
"""
class ListProperty(Property):
	
	def __init__(self,*args,**kwargs):
		
		self._options = kwargs.pop('_options', None)
		
		# Create a new subclass of Schema based on passed in items dict
		self._cls = type('SchemaSubClass', (Schema,), kwargs)
		
		super(ListProperty, self).__init__(self,*args,**kwargs)
	
	# Get
	def __get__(self, instance, owner):
		
		if instance is None:
			# Return descriptor
			return self
		else:
			
			# If first time accessed set default
			if self._name not in instance._propertyValues:
				
				# Create instance of schema subclass
				self.__set__(instance,[])
				
			# Return instance of subclass
			return instance._propertyValues[self._name]
	
	# Set
	def __set__(self, instance, value):
		
		if value == None:
			value = []
		
		# Store a dictpropertylist on the instance
		instance._propertyValues[self._name] = DictPropertyList(value,self._cls)
		

	# Get the object as JSON
	def toDict(self,instance):
		
		# Empty array
		list_data = []
		
		# Loop over dictpropertlist
		for item in self.__get__(instance,None):
		
			list_data.append(item.toDict())
				
		return list_data
	
"""
A couchdb server
"""
class Server(object):
	
	def __init__(self,url):
		self._url = url
		
		# Register all the classes as documents
		Document.registerClasses()
		
	def createDatabase(self,database_name):
		
		# TODO check the database name is valid
		database_url = "%s/%s/" % (self._url, database_name)
		r = requests.put(database_url)
		
		if r.status_code == 201:
			return Database(database_url)
		else:
			raise Exception(r.json())
		
	def getDatabase(self,database_name):
		
		database_url = "%s/%s/" % (self._url, database_name)
		r = requests.get(database_url)
		
		if r.status_code == 200:
			return Database(database_url, info=r.json())
		else:
			raise Exception(r.json())
	
	def databaseExists(self,database_name):
		
		database_url = "%s/_all_dbs" % (self._url)
		r = requests.get(database_url)
		
		if r.status_code == 200:
			return True if database_name in r.json() else False
		else:
			raise Exception(r.json())
		

"""
Represents a couchdb database
"""
class Database(object):
	
	def __init__(self,database_url,info = None):
		self._database_url = database_url
		self._info = info
	
	def getUrl(self):
		return self._database_url
	
	def delete(self):
		r = requests.delete(self._database_url)
		
		if r.status_code == 404:
			raise Exception(r.json())
	
	# Add single document
	def add(self,document):
		
		r = requests.put("%s/%s" % (self._database_url,document._id),data=document.toJson())
		
		if r.status_code == 201:
			document._rev = r.json()["rev"]		
		else:
			raise Exception(r.json())
		
		return document
	
	# Get single document
	def get(self,_id,rev=None):
		
		params = {}
		if rev:
			params = {"rev" : rev}
		
		r = requests.get("%s/%s" % (self._database_url,_id), params = params)
		
		if r.status_code == 200:
			document_data = r.json()
			
			# Get the correct class (if not fall back to document) 
			if document_data["type_"] in Document.typeClassMap:
				document_class = Document.typeClassMap[document_data["type_"]]
			else:
				document_class = Document
			
			return document_class(document_data=document_data)
		
		else:
			raise Exception(r.json())
	
	# Updates a document
	def update(self,document):
		
		r = requests.put("%s/%s" % (self._database_url,document._id),data=document.toJson())
		if r.status_code == 201:
			document._rev = r.json()["rev"]
		else:
			raise Exception(r.json())
		
		return document
	
	# Add link
	def addLink(self,link_property,documents_to_link):
		
		pass

	
"""
The main class to extend. Represents a couchdb schema bound document
"""
class Document(Schema):
	
	# Static to store type again against class
	typeClassMap = {}
	
	# The properties
	_id = StringProperty()
	_rev = StringProperty()
	type_ = StringProperty()
	
	def __init__(self,document_data=None):
		
		Schema.__init__(self)
		
		# See if data passed in
		if document_data == None:
			self._id = uuid.uuid1().hex
			self.type_ = self.__class__.__name__.lower()
		else:
			self.fromDict(document_data)
	
	# Registers all classes that extend Document			
	@staticmethod
	def registerClasses():
		for subclass in all_subclasses(Document):
			Document.typeClassMap[subclass.__name__.lower()] = subclass
	
	# Get the document as JSON
	def toJson(self):
		
		# Empty dict
		document_data = {}
		
		# Loop over properties
		for property_name in self._properties:
			if not (property_name == "_rev" and self._rev == None):
				
				document_data[property_name] = getattr(self.__class__,property_name).toDict(self)		
		
		return json.dumps(document_data)


# Helper to get all subclasses
def all_subclasses(cls):
	return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]

"""
Used to store relationship between documents
"""
class RelationDocument(Document):
	
	type_ = StringProperty(default="_relation")
	name = StringProperty()
	from_type = StringProperty()
	to_type = StringProperty()
	from_id = StringProperty()
	to_id = StringProperty()
	
	def __init__(self,*args,**kwargs):
		Document.__init__(self,*args,**kwargs)

"""
Relation to link documents
"""
"""
class LinkProperty(ObjectProperty):
	
	def __init__(self,linked_class,*args,**kwargs):
		
		self._linked_class = linked_class
		self._reverse = kwargs.pop('reverse', None)
		
		ObjectProperty.__init__(self,*args,**kwargs)
		
		# Add a reverse relation
		if self._reverse and not hasattr(self._linked_class,self._reverse):
			
			setattr(self._linked_class,self._reverse,LinkProperty(self.__class__,reverse=self._name))
		
		
	def __get__(self, instance, owner):
		return self
			
	def __set__(self, instance, value):
		pass
"""
		
		
# User created classes

class Pet(Document):
	
	name = StringProperty(default="dog")
	
	def __init__(self,*args,**kwargs):
		Document.__init__(self,*args,**kwargs)


class Person(Document):
	
	name = StringProperty(default="joe bloggs")
	address = DictProperty(
		address_1 = StringProperty(),
		address_2 = StringProperty(default="wessex"),
		postcode = DictProperty(
			postcode_1 = StringProperty(),
			postcode_2 = StringProperty(),
			extra_postcodes = ListProperty(
				extra_postcode = StringProperty()
			)
		)
	)
	
	other_addresses = ListProperty(
		address_1 = StringProperty(),
		address_2 = StringProperty(default="wessex")
	)
	
	#related_pets = LinkProperty(Pet,reverse="owner")
	
	def __init__(self,*args,**kwargs):
		Document.__init__(self,*args,**kwargs)
		




if __name__ == "__main__":

	server = Server("http://127.0.0.1:5984")
	
	if not server.databaseExists("test"):
		db = server.createDatabase("test")
	else:
		db = server.getDatabase("test")
	
	
	person = Person()
	person1 = Person()
	

	person.name = "will"
	person.address.address_1 = "1 boltro road"
	person.address.postcode.postcode_1 = "RH16"
	person.other_addresses.append({"address_1":"my street","address_2":"UK"})

	
	person1.name = "kate"
	person1.address.address_1 = "1 home road"
	person1.address.postcode.postcode_1 = "HN3"
	
	print person.toJson()
	print person1.toJson()
	
	person = db.add(person)
	person1 = db.add(person1)
	
	#pet = Pet()
	#db.addLink(person.related_pets, pet)
	
	
	#print person.name
	#print person1.name
	person_fetched = db.get(person._id)
	person1_fetched = db.get(person1._id)
	
	print person_fetched.toJson()
	print person1_fetched.toJson()
	
