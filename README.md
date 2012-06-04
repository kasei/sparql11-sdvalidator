SPARQL 1.1 Service Description Validator
==================================

This repository contains code which attempts to validate implementations of the
[SPARQL 1.1 Service Description](http://www.w3.org/TR/sparql11-service-description/).

The validator is implemented as a perl CGI, and depends on packages available
from [CPAN](https://metacpan.org/):

* [JSON](https://metacpan.org/release/JSON)
* [RDF::Trine](https://metacpan.org/release/RDF-Trine)

Tests
-----

The validator comprises three tests which correspond to the
[conformance criteria](http://www.w3.org/TR/sparql11-service-description/#conformance).

* returns-rdf - The SPARQL service must return RDF content when the service
  endpoint URL is accessed

* has-endpoint-triple - The RDF returned from an endpoint URL <tt>&lt;U></tt> must
  include at least one triple matching the pattern:

		?service sd:endpoint <U>

* conforms-to-schema - The RDF returned must make use of the Service Description
  vocabulary in accordance with the usage specified in
  [Service Description Vocabulary](http://www.w3.org/TR/sparql11-service-description/#vocab).
  As this is difficult to test thouroughly while remaining extensible, this test
  currently verifies only one aspect of the vocabulary use: all <tt>sd:NamedGraph</tt>s
  must have a <tt>sd:name</tt> property.
  
