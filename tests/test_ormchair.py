'''
Created on 19 Apr 2013

@author: Will Ogden
'''
import unittest
import ormchair

class SchemaTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchema(ormchair.Schema):
			string_property = ormchair.StringProperty()
			number_property = ormchair.NumberProperty()
			integer_property = ormchair.IntegerProperty()
			boolean_property = ormchair.BooleanProperty()
			list_property = ormchair.ListProperty(
				ormchair.StringProperty()
			)
			dict_property = ormchair.DictProperty(
				string_property = ormchair.StringProperty(),
			)
			
		self.schema_class = TestSchema

	def tearDown(self):
		
		self.schema_class = None

	def test_property_types(self):
		
		self.assertIsInstance(self.schema_class.string_property,ormchair.StringProperty)
		self.assertIsInstance(self.schema_class.number_property,ormchair.NumberProperty)
		self.assertIsInstance(self.schema_class.integer_property,ormchair.IntegerProperty)
		self.assertIsInstance(self.schema_class.boolean_property,ormchair.BooleanProperty)
		self.assertIsInstance(self.schema_class.list_property,ormchair.ListProperty)
		self.assertIsInstance(self.schema_class.dict_property,ormchair.DictProperty)
		
	def test_schema_to_dict(self):
		
		schema_dict = {
			'$schema': 'http://json-schema.org/draft-03/schema#', 
			'id': 'testschema',
			'type': 'object', 
			'properties': {
				'string_property': {
					'type': 'string'
				},
				'integer_property': {
					'type': 'integer'
				},
				'boolean_property': {
					'type': 'boolean'
				},
				'dict_property': {
					'type': 'object', 
					'properties': {
						'string_property': {
							'type': 'string'
						}
					}
				},
				'list_property': {
					'items': {
						'type': 'string'
					}
				},
				'number_property': {
					'type': 'number'
				}
			}
		}
		
		
		self.assertEqual(self.schema_class.schemaToDict(), schema_dict)

	def test_schema_instance_to_dict(self):
		
		schema_instance = self.schema_class()
		
		schema_instance.string_property = "a string property"
		schema_instance.number_property = 100.01
		schema_instance.integer_property = 100
		schema_instance.boolean_property = False
		schema_instance.list_property = ["string item 1","string item 2"]
		schema_instance.dict_property.string_property = "a string property"
		
		schema_instance_dict = {
			'string_property': 'a string property', 
			'integer_property': 100, 
			'boolean_property': False, 
			'dict_property': {
				'string_property': 'a string property'
			}, 
			'list_property': [
				'string item 1', 
				'string item 2'
			],
			'number_property': 100.01
		}
		
		self.assertEqual(schema_instance.instanceToDict(),schema_instance_dict)
		
	def test_dict_to_schema_instance(self):
		
		schema_instance = self.schema_class()
		
		schema_instance_dict = {
			'string_property': 'a string property', 
			'integer_property': 100, 
			'boolean_property': False, 
			'dict_property': {
				'string_property': 'a string property'
			}, 
			'list_property': [
				'string item 1', 
				'string item 2'
			],
			'number_property': 100.01
		}
		
		schema_instance.instanceFromDict(schema_instance_dict)
		self.assertEqual(schema_instance.string_property,"a string property")
		self.assertEqual(schema_instance.number_property,100.01)
		self.assertEqual(schema_instance.integer_property,100)
		self.assertEqual(schema_instance.boolean_property,False)
		self.assertListEqual(schema_instance.list_property,['string item 1','string item 2'])
		self.assertDictEqual(schema_instance.__class__.dict_property.instanceToDict(schema_instance),{'string_property':'a string property'})
		
	def test_root_instance(self):
		
		schema_instance = self.schema_class()
		
		self.assertEqual(schema_instance,schema_instance.getRootInstance())
		self.assertEqual(schema_instance,schema_instance.dict_property.getRootInstance())
		
class StringPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchema(ormchair.Schema):
			string_property_1 = ormchair.StringProperty(required=True)
			string_property_2 = ormchair.StringProperty(default="Here's a test")
			string_property_3 = ormchair.StringProperty(min_length=5)
			string_property_4 = ormchair.StringProperty(max_length=5)
			
		self.schema_class = TestSchema

	def tearDown(self):
		
		self.schema_class = None
	
	def test_is_required(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"string_property_2" : "Another test"})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
		
			
	def test_default_value(self):
		
		schema_instance = self.schema_class()
		
		self.assertNotEqual(schema_instance.string_property_1, "Here's a test")
		self.assertEqual(schema_instance.string_property_2, "Here's a test")
		
	def test_min_length(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"string_property_1" : "Another test","string_property_3" : "tes"})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
	
	def test_max_length(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"string_property_1" : "Another test","string_property_4" : "testss"})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)

class NumberPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchema(ormchair.Schema):
			number_property_1 = ormchair.NumberProperty(required=True)
			number_property_2 = ormchair.NumberProperty(default=2.34)
			number_property_3 = ormchair.NumberProperty(minimum=5)
			number_property_4 = ormchair.NumberProperty(maximum=5)
			
		self.schema_class = TestSchema

	def tearDown(self):
		
		self.schema_class = None
	
	def test_is_required(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"number_property_2" : 3})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
		
			
	def test_default_value(self):
		
		schema_instance = self.schema_class()
		
		self.assertNotEqual(schema_instance.number_property_1, 2.34)
		self.assertEqual(schema_instance.number_property_2, 2.34)
		
	def test_minimum(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"number_property_1" : 4,"number_property_3" : 4})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
	
	def test_maximum(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"number_property_1" : 4,"number_property_4" : 6})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
			
class IntegerPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchema(ormchair.Schema):
			integer_property_1 = ormchair.IntegerProperty(required=True)
			integer_property_2 = ormchair.IntegerProperty(default=2)

		self.schema_class = TestSchema

	def tearDown(self):
		
		self.schema_class = None
	
	def test_is_required(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"integer_property_2" : 3})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
		
	def test_default_value(self):
		
		schema_instance = self.schema_class()
		
		self.assertNotEqual(schema_instance.integer_property_1, 2)
		self.assertEqual(schema_instance.integer_property_2, 2)
		
	def test_not_integer(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"integer_property_1" : 4.4})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)

class BooleanPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchema(ormchair.Schema):
			boolean_property_1 = ormchair.BooleanProperty(required=True)
			boolean_property_2 = ormchair.BooleanProperty(default=False)

		self.schema_class = TestSchema

	def tearDown(self):
		
		self.schema_class = None
	
	def test_is_required(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"boolean_property_2" : True})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
		
	def test_default_value(self):
		
		schema_instance = self.schema_class()
		
		self.assertNotEqual(schema_instance.boolean_property_1, False)
		self.assertEqual(schema_instance.boolean_property_2, False)
		
	def test_not_boolean(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"boolean_property_1" : 2})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)

class DictPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchema(ormchair.Schema):
			dict_property_1 = ormchair.DictProperty(required=True,
				string_property_1 = ormchair.StringProperty()
			)
			dict_property_2 = ormchair.DictProperty(default={"string_property_1": "test", "number_property_2" : 10},
				string_property_1 = ormchair.StringProperty(),
				number_property_2 = ormchair.NumberProperty()
			)

		self.schema_class = TestSchema

	def tearDown(self):
		
		self.schema_class = None
	
	def test_is_required(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"dict_property_2" : {"string_property_1": "test", "number_property_2" : 10}})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
		
	def test_default_value(self):
		
		schema_instance = self.schema_class()
		
		self.assertNotEqual(schema_instance.__class__.dict_property_1.instanceToDict(schema_instance), {"string_property_1": "test", "number_property_2" : 10})
		self.assertDictEqual(schema_instance.__class__.dict_property_2.instanceToDict(schema_instance), {"string_property_1": "test", "number_property_2" : 10})
		
	def test_not_dict_property(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"dict_property_1" : {"wrong_property" : 23}})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
			
class ListPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchema(ormchair.Schema):
			list_property_1 = ormchair.ListProperty(
				ormchair.StringProperty(),
				required=True
			)
			list_property_2 = ormchair.ListProperty(
				ormchair.DictProperty(
					string_property_1 = ormchair.StringProperty(),
					number_property_2 = ormchair.NumberProperty()
					
				),
				default=[{"string_property_1": "test", "number_property_2" : 10}]
			)
			list_property_3 = ormchair.ListProperty(
				ormchair.DictProperty(
					nested_list_property = ormchair.ListProperty(
						ormchair.DictProperty(
							string_property_3 = ormchair.StringProperty()
						)
					)
				)
			)

		self.schema_class = TestSchema

	def tearDown(self):
		
		self.schema_class = None
	
	def test_is_required(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"list_property_2" : [{"string_property_1": "test", "number_property_2" : 10}]})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
		
	def test_default_value(self):
		
		schema_instance = self.schema_class()
		
		self.assertNotEqual(schema_instance.__class__.list_property_1.instanceToDict(schema_instance), [{"string_property_1": "test", "number_property_2" : 10}])
		self.assertListEqual(schema_instance.__class__.list_property_2.instanceToDict(schema_instance), [{"string_property_1": "test", "number_property_2" : 10}])
		
	def test_not_list_property(self):
		
		schema_instance = self.schema_class()
		
		try:
			schema_instance.instanceFromDict({"list_property_1" : [{"wrong_property" : 23}]})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
	
	def test_nested_list_and_dict(self):
		
		schema_instance = self.schema_class()
		schema_instance.list_property_3.append({"nested_list_property":[{"string_property_3": "Test"}]})
		schema_instance.list_property_3[0].nested_list_property.append({"string_property_3": "Test2"})
		self.assertListEqual(schema_instance.__class__.list_property_3.instanceToDict(schema_instance), [{"nested_list_property":[{"string_property_3": "Test"}, {"string_property_3": "Test2"}]}])

class EmbeddedLinkPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchemaA(ormchair.BaseDocument):
			string_property_1 = ormchair.StringProperty()
		
		schema_instance_a = TestSchemaA()
		schema_instance_a._id = "Test ID"
		
		class TestSchemaB(ormchair.BaseDocument):
			embeddeded_link_property_1 = ormchair.EmbeddedLinkProperty(
				TestSchemaA,
				required=True
			)
			embeddeded_link_property_2 = ormchair.EmbeddedLinkProperty(
				TestSchemaA,
				default=schema_instance_a
			)

		self.schema_class_a = TestSchemaA
		self.schema_class_b = TestSchemaB
		self.schema_instance_a = schema_instance_a

	def tearDown(self):
		
		self.schema_class_a = None
		self.schema_class_b = None
	
	def test_is_required(self):
		
		schema_instance_a = self.schema_class_a()
		schema_instance_b = self.schema_class_b()
		
		try:
			schema_instance_a.instanceFromDict({"embeddeded_link_property_2" : schema_instance_b})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
		
	def test_default_value(self):
		
		schema_instance_b = self.schema_class_b()
		
		self.assertNotEqual(schema_instance_b.embeddeded_link_property_1, self.schema_instance_a)
		self.assertEqual(schema_instance_b.embeddeded_link_property_2, self.schema_instance_a)
		
	
	def test_not_embedded_link_property(self):
		
		schema_instance_b = self.schema_class_b()
		
		try:
			schema_instance_b.instanceFromDict({"embeddeded_link_property_1" : {"wrong_property" : 23}})
			self.fail()
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
	
	def test_only_link_to_basedocuments(self):
		
		try:
			class TestSchemaC(ormchair.Schema):
				string_property_1 = ormchair.StringProperty()
		
		except Exception as e:
			self.assertIsInstance(e,ormchair.ValidationError)
			
class LinkPropertyTestCase(unittest.TestCase):
	
	def setUp(self):
		
		class TestSchemaA(ormchair.BaseDocument):
			pass
		
		class TestSchemaB(ormchair.BaseDocument):
			link_property_to_a = ormchair.LinkProperty(TestSchemaA,reverse="link_property_to_b")

		self.schema_class_a = TestSchemaA
		self.schema_class_b = TestSchemaB

	def tearDown(self):
		
		self.schema_class_a = None
		self.schema_class_b = None
	
	def test_return_type(self):
		
		schema_instance_b = self.schema_class_b()
		(instance,property) = schema_instance_b.link_property_to_a
		
		self.assertEqual(schema_instance_b,instance)
		self.assertEqual(schema_instance_b.__class__.link_property_to_a,property)
	
	def test_reverse_property(self):
		
		schema_instance_b = self.schema_class_b()
		
		linked_class = schema_instance_b.__class__.link_property_to_a.getLinkedClass()
		reverse_property_name = schema_instance_b.__class__.link_property_to_a.getReverse()
		
		self.assertTrue(hasattr(linked_class,reverse_property_name))
		self.assertIsInstance(getattr(linked_class,reverse_property_name), ormchair.LinkProperty)

class SessionTestCase(unittest.TestCase):
	
	def setUp(self):
		
		self.session = ormchair.Session("http://127.0.0.1:5984",username="testadmin", password="testadmin")
		if self.session.databaseExists("test_ormchair"):
			self.session.deleteDatabase("test_ormchair")

	def tearDown(self):
		
		self.session = None
		
	def test_create_database(self):
		
		test_ormchair_db = self.session.createDatabase("test_ormchair")
		self.assertIsInstance(test_ormchair_db,ormchair.Database)
		
	
	def test_get_database(self):
		
		self.session.createDatabase("test_ormchair")
		test_ormchair_db = self.session.getDatabase("test_ormchair")
		self.assertIsInstance(test_ormchair_db,ormchair.Database)

			
	def test_delete_database(self):
		
		self.session.createDatabase("test_ormchair")
		self.assertTrue(self.session.databaseExists("test_ormchair"))
		self.session.deleteDatabase("test_ormchair")
		self.assertFalse(self.session.databaseExists("test_ormchair"))
		
class DatabaseTestCase(unittest.TestCase):
	
	def setUp(self):
		
		self.session = ormchair.Session("http://127.0.0.1:5984",username="testadmin", password="testadmin")
		
		if self.session.databaseExists("test_ormchair"):
			self.session.deleteDatabase("test_ormchair")
		
		self.test_ormchair_db = self.session.createDatabase("test_ormchair")
		
		# Test data
		@ormchair._id("_design/all_pets")
		class AllPetsDesignDocument(ormchair.DesignDocument):
			
			all_pets = ormchair.View({
				"map" :(
					'function(doc) {'
						'if(doc.type_=="pet") {'
							'emit(doc._id,null);'
						'}'
					'}'
				)
			})
		
		
		class Pet(ormchair.Document):
	
			name = ormchair.StringProperty(default="dog")
			
			all = ormchair.View({
				"map" :(
					'function(doc) {'
						'if(doc.type_=="pet") {'
							'emit(doc._id,null);'
						'}'
					'}'
				)
			})
			
			get_by_name = ormchair.Index("name")
				
		
		class Person(ormchair.Document):
			
			name = ormchair.StringProperty(default="joe bloggs")
			address = ormchair.DictProperty(
				address_1 = ormchair.StringProperty(),
				address_2 = ormchair.StringProperty(default="wessex"),
				postcode = ormchair.DictProperty(
					postcode_1 = ormchair.StringProperty(),
					postcode_2 = ormchair.StringProperty(),
					extra_postcodes = ormchair.ListProperty(
						ormchair.StringProperty()
					)
				)
			)
			
			other_addresses = ormchair.ListProperty(
				ormchair.DictProperty(
					address_1 = ormchair.StringProperty(),
					address_2 = ormchair.StringProperty(default="wessex")
				)
			)
			
			related_pets = ormchair.LinkProperty(Pet,reverse="owner")
			
			best_pet = ormchair.EmbeddedLinkProperty(Pet)
			
			owned_pets = ormchair.ListProperty(
				ormchair.EmbeddedLinkProperty(Pet)
			)
			
			
			get_by_name = ormchair.Index("name")
			get_by_name_and_address = ormchair.Index("name","address.address_1")
		
		self.pet_class = Pet
		self.person_class = Person
		
		self.test_ormchair_db.sync()
		
	def tearDown(self):
		
		self.session = None
	
	def test_sync(self):
		
		all_pets_design_document = self.test_ormchair_db.get("_design/all_pets")
		pet_schema_design_document = self.test_ormchair_db.get(self.pet_class.getSchemaDesignDocumentId())
		person_schema_design_document = self.test_ormchair_db.get(self.person_class.getSchemaDesignDocumentId())
		
		self.assertTrue(issubclass(all_pets_design_document.__class__,ormchair.DesignDocument))
		self.assertTrue(issubclass(pet_schema_design_document.__class__,ormchair.DesignDocument))
		self.assertTrue(issubclass(person_schema_design_document.__class__,ormchair.DesignDocument))
		
		self.assertTrue(len(all_pets_design_document._rev)>0)
		self.assertTrue(len(pet_schema_design_document._rev)>0)
		self.assertTrue(len(person_schema_design_document._rev)>0)
	
	def test_add_document(self):
		
		person1 = self.person_class()
		person1.name = "Will"
		
		person2 = self.person_class()
		person2.name = "Tom"
		
		pet1 = self.pet_class()
		pet1.name = "Pooch"
		
		pet2 = self.pet_class()
		pet2.name = "Snoop"
		
		self.assertNotEqual(person1.name, person2.name)
		
def suite():
	
	suite = unittest.TestSuite()
	
	suite.addTest(SchemaTestCase('test_property_types'))
	suite.addTest(SchemaTestCase('test_schema_to_dict'))
	suite.addTest(SchemaTestCase('test_schema_instance_to_dict'))
	suite.addTest(SchemaTestCase('test_dict_to_schema_instance'))
	suite.addTest(SchemaTestCase('test_root_instance'))
	
	suite.addTest(StringPropertyTestCase('test_is_required'))
	suite.addTest(StringPropertyTestCase('test_default_value'))
	suite.addTest(StringPropertyTestCase('test_min_length'))
	suite.addTest(StringPropertyTestCase('test_max_length'))
	
	suite.addTest(NumberPropertyTestCase('test_is_required'))
	suite.addTest(NumberPropertyTestCase('test_default_value'))
	suite.addTest(NumberPropertyTestCase('test_minimum'))
	suite.addTest(NumberPropertyTestCase('test_maximum'))
	
	suite.addTest(IntegerPropertyTestCase('test_is_required'))
	suite.addTest(IntegerPropertyTestCase('test_default_value'))
	suite.addTest(IntegerPropertyTestCase('test_not_integer'))
	
	suite.addTest(BooleanPropertyTestCase('test_is_required'))
	suite.addTest(BooleanPropertyTestCase('test_default_value'))
	suite.addTest(BooleanPropertyTestCase('test_not_boolean'))
	
	suite.addTest(DictPropertyTestCase('test_is_required'))
	suite.addTest(DictPropertyTestCase('test_default_value'))
	suite.addTest(DictPropertyTestCase('test_not_dict_property'))
	
	suite.addTest(ListPropertyTestCase('test_is_required'))
	suite.addTest(ListPropertyTestCase('test_default_value'))
	suite.addTest(ListPropertyTestCase('test_not_list_property'))
	suite.addTest(ListPropertyTestCase('test_nested_list_and_dict'))
	
	suite.addTest(EmbeddedLinkPropertyTestCase('test_is_required'))
	suite.addTest(EmbeddedLinkPropertyTestCase('test_default_value'))
	suite.addTest(EmbeddedLinkPropertyTestCase('test_not_embedded_link_property'))
	suite.addTest(EmbeddedLinkPropertyTestCase('test_only_link_to_basedocuments'))
	
	suite.addTest(LinkPropertyTestCase('test_return_type'))
	suite.addTest(LinkPropertyTestCase('test_reverse_property'))
	
	suite.addTest(SessionTestCase('test_create_database'))
	suite.addTest(SessionTestCase('test_get_database'))
	suite.addTest(SessionTestCase('test_delete_database'))
	
	suite.addTest(DatabaseTestCase('test_sync'))
	return suite

if __name__ == "__main__":
	
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main(defaultTest='suite')