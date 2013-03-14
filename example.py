'''
Created on 14 Mar 2013

@author: will ogden
'''
import json
from ormchair import Server,Document,StringProperty,DictProperty,ListProperty,LinkProperty,EmbeddedLinkProperty

# User created classes

class Pet(Document):
	
	name = StringProperty(default="dog")
		

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
	
	related_pets = LinkProperty(Pet,type="one_to_many",reverse="owner")
	
	best_pet = EmbeddedLinkProperty(Pet)
	
	owned_pets = ListProperty(
		pet = EmbeddedLinkProperty(Pet)
	)
		

if __name__ == "__main__":

	server = Server("http://127.0.0.1:5984")
	
	if not server.databaseExists("test"):
		db = server.createDatabase("test")
	else:
		db = server.getDatabase("test")
	
	
	person = Person()
	person1 = Person()
	

	person.name = "will"
	person.address.address_1 = "1 work road"
	person.address.postcode.postcode_1 = "RH16"
	person.other_addresses.append({"address_1":"my street","address_2":"UK"})

	
	person1.name = "kate"
	person1.address.address_1 = "1 home road"
	person1.address.postcode.postcode_1 = "HN3"
	
	print person.toJson()
	print person1.toJson()
	
	db.add(person)
	db.add(person1)
	
	person1.name = "Jon"
	old_rev = person1._rev
	db.update(person1)
	person1._rev = old_rev
	person.name = "WILLIAM"
	person1.name = "KALENA"
	
	(ok_docs,failed_docs) = db.updateMultiple([person,person1])
	print "update - ok",ok_docs
	print "update - failed",failed_docs
	
	pet = Pet()
	pet1 = Pet()
	db.addMultiple([pet,pet1])
	db.addLink(person.related_pets, pet)
	
	updated_pets = db.getMultiple([pet._id,pet1._id])
	for upet in updated_pets:
		print upet
		
	person.best_pet = pet
	person.owned_pets.append({"pet": pet1})
	print "person best pet inflated",person.best_pet
	db.update(person)
	
	#print person.name
	#print person1.name
	person_fetched = db.get(person._id)
	person1_fetched = db.get(person1._id)
	
	print "person best pet not inflated",person_fetched.best_pet
	
	print person_fetched.toJson()
	#print person1_fetched.toJson()
	
	print json.dumps(Person.schemaToDict())

