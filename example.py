'''
Created on 14 Mar 2013

@author: will ogden
'''
import json
from ormchair import Server,Document,DesignDocument,View,Index,StringProperty,DictProperty,ListProperty,LinkProperty,EmbeddedLinkProperty,_id,_SchemaDesignDocument

# User created classes
@_id("_design/tester")
class TestDesignDocument(DesignDocument):
	
	all2 = View({
		"map" :(
			"function(doc) {"
				"emit('test2',doc);"
			"}"
		)
	})
	
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
				StringProperty()
			)
		)
	)
	
	other_addresses = ListProperty(
		DictProperty(
			address_1 = StringProperty(),
			address_2 = StringProperty(default="wessex")
		)
	)
	
	related_pets = LinkProperty(Pet,reverse="owner")
	
	best_pet = EmbeddedLinkProperty(Pet)
	
	owned_pets = ListProperty(
		EmbeddedLinkProperty(Pet)
	)
	
	test_property = StringProperty()
	
	get_by_name = Index("name")
	get_by_name_and_address = Index("name","address.address_1")
		

if __name__ == "__main__":

	server = Server("http://127.0.0.1:5984")
	
	if not server.databaseExists("test"):
		db = server.createDatabase("test")
	else:
		db = server.getDatabase("test")
	
	db.sync()
	
	
	person = Person()
	person1 = Person()
	

	person.name = "will"
	person.address.address_1 = "1 work road"
	person.address.postcode.postcode_1 = "RH16"
	person.other_addresses.extend([{"address_1":"my street","address_2":"UK"},{"address_1":"44 the toad","address_2":"USA"}])
	print person.other_addresses[1]
	
	person1.name = "kate"
	person1.address.address_1 = "1 home road"
	person1.address.postcode.postcode_1 = "HN3"
	
	print person.instanceToDict()
	print person1.instanceToDict()
	
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
	person.owned_pets.append(pet1)
	print "person best pet inflated",person.best_pet
	db.update(person)
	
	#print person.name
	#print person1.name
	person_fetched = db.get(person._id)
	person1_fetched = db.get(person1._id)
	
	print "person best pet not inflated",person_fetched.best_pet
	
	print person_fetched.instanceToDict()
	#print person1_fetched.instanceToDict()
	
	print json.dumps(Person.schemaToDict())
	
	queried_persons = db.getByIndex(Person.get_by_name,["WILLIAM"])
	for queried_person in queried_persons:
		print queried_person.name
	
	persons_pets = db.getLinks(person.related_pets,limit=1)
	print persons_pets
	
	test_doc = _SchemaDesignDocument()
	test_doc.links_["map"] = "function(doc){}";
	test_doc1 = _SchemaDesignDocument()
	print test_doc1.instanceToDict()