#!/usr/bin/perl

use strict;
use warnings;
use lib qw(lib);
use CGI qw(Accept);
use JSON;
use RDF::Trine qw(statement iri literal blank);
use RDF::Trine::Error qw(:try);
use RDF::Trine::Namespace qw(rdf dc xsd);

use constant {
	PASS	=> 'pass',
	FAIL	=> 'fail',
};

use constant {
	TEST_SD_REQ_RETURNS_RDF			=> 'returns-rdf',
	TEST_SD_REQ_ENDPOINT_TRIPLE		=> 'has-endpoint-triple',
	TEST_SD_REQ_CONFORMS_TO_SCHEMA	=> 'conforms-to-schema',
	###
	TEST_SD_OPT_TYPED_SERVICE		=> 'typed-service',
	TEST_SD_OPT_TYPED_DATASET		=> 'typed-dataset',
	TEST_SD_OPT_TYPED_NAMEDGRAPH	=> 'typed-named-graph',
	TEST_SD_OPT_TYPED_GRAPH			=> 'typed-graph',
	TEST_SD_OPT_RECOGNIZED_LANG		=> 'recognized-language',
	TEST_SD_OPT_DATASET_WITH_GRAPH	=> 'dataset-with-graph',
};

use constant REQUIRED_TESTS	=> (TEST_SD_REQ_RETURNS_RDF(), TEST_SD_REQ_ENDPOINT_TRIPLE(), TEST_SD_REQ_CONFORMS_TO_SCHEMA());
use constant OPTIONAL_TESTS	=> (TEST_SD_OPT_TYPED_SERVICE(), TEST_SD_OPT_TYPED_DATASET(), TEST_SD_OPT_TYPED_NAMEDGRAPH(), TEST_SD_OPT_TYPED_GRAPH(), TEST_SD_OPT_DATASET_WITH_GRAPH(), TEST_SD_OPT_RECOGNIZED_LANG());

use constant DESCRIPTION => {
	TEST_SD_REQ_RETURNS_RDF()			=> 'GET on endpoint returns RDF',
	TEST_SD_REQ_ENDPOINT_TRIPLE()		=> 'Service description contains a matching sd:endpoint triple',
	TEST_SD_REQ_CONFORMS_TO_SCHEMA()	=> 'Service description conforms to schema',
	###
	TEST_SD_OPT_TYPED_SERVICE()			=> 'All potential service are typed as sd:Service',
	TEST_SD_OPT_TYPED_DATASET()			=> 'All potential datasets are typed as sd:Dataset',
	TEST_SD_OPT_TYPED_NAMEDGRAPH()		=> 'All potential named graphs are typed as sd:NamedGraph',
	TEST_SD_OPT_TYPED_GRAPH()			=> 'All potential graphs are typed as sd:Graph',
	TEST_SD_OPT_DATASET_WITH_GRAPH()	=> 'All datasets have either a default or a named graph',
	TEST_SD_OPT_RECOGNIZED_LANG()		=> 'Recognized sd:supportedLanguage IRI',
};

our $VALIDATOR_IRI	= 'http://www.w3.org/2009/sparql/sdvalidator#validator';
my $earl			= RDF::Trine::Namespace->new( 'http://www.w3.org/ns/earl#' );
my $sd				= RDF::Trine::Namespace->new( 'http://www.w3.org/ns/sparql-service-description#' );
my $sdtest			= RDF::Trine::Namespace->new( 'http://www.w3.org/2009/sparql/docs/tests/data-sparql11/service-description/manifest#' );
my $q				= new CGI;

run($q);

sub run {
	my $q	= shift;
	my $url		= $q->param('url');
	my $opt		= $q->param('bp') ? 1 : 0;
	
	if ($url) {
		my $res	= validate($url, $opt);
		show_results($url, $res, $opt, $q);
	} else {
		print $q->header( -type => 'text/html', -charset => 'utf-8');
		print_html_header();
		print_form('', '');
		print_html_footer();
	}
}

sub passed {
	my $res		= shift;
	my $test	= shift;
	my $type	= test_type($test);
	return ($res->{$type}{$test}{result} eq PASS);
}

sub test_messages {
	my $res		= shift;
	my $test	= shift;
	my $type	= test_type($test);
	my $msg		= $res->{$type}{$test}{message};
	if (ref($msg)) {
		return @$msg;
	} else {
		return ($msg);
	}
}

sub test_type {
	my $test	= shift;
	foreach my $t (REQUIRED_TESTS) {
		return 'required' if ($test eq $t);
	}
	return 'optional';
}

sub add_result {
	my $res		= shift;
	my $test	= shift;
	my $status	= shift;
	my $mesg	= shift;
	my $type	= test_type($test);
	my $desc	= DESCRIPTION->{ $test };
	$res->{$type}{$test}	= { result => $status, description => $desc };
	if ($mesg) {
		$res->{$type}{$test}{ message }	= $mesg;
	}
}

sub update_result {
	my $res		= shift;
	my $test	= shift;
	my $status	= shift;
	my $mesg	= shift;
	my $type	= test_type($test);
	my $desc	= DESCRIPTION->{ $test };
	if (exists($res->{$test})) {
		my $result	= $res->{$type}{$test}{result};
		if ($result eq PASS and $status eq FAIL) {
			$res->{$type}{$test}{result}	= FAIL;
		}
		if ($mesg) {
			push(@{ $res->{$type}{$test}{ message } }, $mesg);
		}
	} else {
		$res->{$type}{$test}	= { result => $status, description => $desc };
		if ($mesg) {
			$res->{$type}{$test}{ message }	= [ $mesg ];
		}
	}
}

sub validate {
	my $url		= shift;
	my $opt		= shift;
	my $model	= RDF::Trine::Model->new();
	my $res		= {};
	my $pass	= 0;
	
	try {
		RDF::Trine::Parser->parse_url_into_model( $url, $model );
		add_result( $res, TEST_SD_REQ_RETURNS_RDF, PASS );
		$pass	= 1;
	} catch RDF::Trine::Error::ParserError with {
		my $e	= shift;
		add_result( $res, TEST_SD_REQ_RETURNS_RDF, FAIL, "Error: " . $e->text );
	};
	
	if ($pass) {
		{
			my $iri	= iri($url);
			my $iter	= $model->get_statements( undef, $sd->endpoint, $iri );
			my @st		= $iter->get_all();
			if (scalar(@st) ) {
				add_result( $res, TEST_SD_REQ_ENDPOINT_TRIPLE, PASS );
			} else {
				add_result( $res, TEST_SD_REQ_ENDPOINT_TRIPLE, FAIL );
			}
		}
		
		{
			my @ng	= $model->subjects( $rdf->type, $sd->NamedGraph );
			my @bad;
			foreach my $n (@ng) {
				my @names	= $model->objects( $n, $sd->name );
				if (scalar(@names) == 0) {
					push(@bad, $n);
				}
			}
			if (scalar(@bad)) {
				my @strings	= map { $_->as_ntriples } @bad;
				my $msg	= sprintf("NamedGraphs do not have a sd:name value: %s", join(', ', @strings));
				update_result( $res, TEST_SD_REQ_CONFORMS_TO_SCHEMA, FAIL, $msg );
			} else {
				update_result( $res, TEST_SD_REQ_CONFORMS_TO_SCHEMA, PASS );
			}
		}
	}
	
	if ($opt) {
		optional_tests($res, $model);
	}
	
	return $res;
}

sub optional_tests {
	my $res		= shift;
	my $model	= shift;
	
	# TEST_SD_OPT_TYPED_SERVICE
	test_types(
		$res,
		$model,
		TEST_SD_OPT_TYPED_SERVICE,
		$sd->Service,
		"Services are not explicitly typed as sd:Service",
		domains	=> [$sd->endpoint, $sd->feature, $sd->defaultEntailmentRegime, $sd->defaultSupportedEntailmentProfile, $sd->extensionFunction, $sd->extensionAggregate, $sd->languageExtension, $sd->supportedLanguage, $sd->propertyFeature, $sd->defaultDataset, $sd->availableGraphs, $sd->resultFormat, $sd->inputFormat],
	);

	# TEST_SD_OPT_TYPED_DATASET
	my @datasets	= test_types(
		$res,
		$model,
		TEST_SD_OPT_TYPED_DATASET,
		$sd->Dataset,
		"Datasets are not explicitly typed as sd:Dataset",
		domains	=> [$sd->defaultGraph],
		ranges	=> [$sd->defaultDataset],
	);

	# TEST_SD_OPT_TYPED_NAMEDGRAPH
	test_types(
		$res,
		$model,
		TEST_SD_OPT_TYPED_NAMEDGRAPH,
		$sd->NamedGraph,
		"NamedGraphs are not explicitly typed as sd:NamedGraph",
		domains	=> [$sd->entailmentRegime, $sd->supportedEntailmentProfile, $sd->name, $sd->graph],
		ranges	=> [$sd->namedGraph],
	);

	# TEST_SD_OPT_TYPED_GRAPH
	test_types(
		$res,
		$model,
		TEST_SD_OPT_TYPED_GRAPH,
		$sd->Graph,
		"Graphs are not explicitly typed as sd:Graph",
		ranges	=> [$sd->defaultGraph, $sd->graph],
	);
	
	# TEST_SD_OPT_RECOGNIZED_LANG
	{
		my @langs	= $model->objects( undef, $sd->supportedLanguage );
		my $recognized	= 0;
		foreach my $l (@langs) {
			next unless ($l->isa('RDF::Trine::Node::Resource'));
			my $iri	= $l->uri_value;
			$recognized++ if ($iri =~ m[^http://www[.]w3[.]org/ns/sparql-service-description#SPARQL(10Query|11Query|11Update)$]);
		}
		if ($recognized) {
			add_result( $res, TEST_SD_OPT_RECOGNIZED_LANG, PASS );
		} else {
			my $msg	= "No recognized SPARQL 1.0 or 1.1 sd:Language instances are used with the sd:supportedLanguage property";
			add_result( $res, TEST_SD_OPT_RECOGNIZED_LANG, FAIL, $msg );
		}
	}
	
	# TEST_SD_OPT_DATASET_WITH_GRAPH
	{
		my @bad;
		foreach my $ds (@datasets) {
			my $graphs	= $model->count_statements( $ds, $sd->defaultGraph );
			my $named	= $model->count_statements( $ds, $sd->namedGraph );
			my $total	= $graphs + $named;
			if ($total == 0) {
				push(@bad, $ds);
			}
		}
		
		if (scalar(@bad)) {
			my @strings	= map { $_->as_ntriples } @bad;
			my $msg	= sprintf("Datasets do not have a default graph or any named graphs: %s", join(', ', @strings));
			add_result( $res, TEST_SD_OPT_DATASET_WITH_GRAPH, FAIL, $msg );
		} else {
			add_result( $res, TEST_SD_OPT_DATASET_WITH_GRAPH, PASS );
		}
	}
}

sub test_types {
	my $res		= shift;
	my $model	= shift;
	my $test	= shift;
	my $type	= shift;
	my $error	= shift;
	my %props	= @_;
	
	my @candidates;
	if (my $props = $props{ domains }) {
		push(@candidates, map { $model->subjects($_) } @$props);
	}
	if (my $props = $props{ ranges }) {
		push(@candidates, map { $model->objects(undef, $_) } @$props);
	}
	
	my @bad;
	my %seen;
	my @return_candidates;
	foreach my $s (@candidates) {
		next if ($seen{ $s->as_string }++);
		push(@return_candidates, $s);
		my $count	= $model->count_statements( $s, $rdf->type, $type );
		if ($count == 0) {
			push(@bad, $s);
		}
	}
	
	if (scalar(@bad)) {
		my @strings	= map { $_->as_ntriples } @bad;
		my $msg	= sprintf("$error: %s", join(', ', @strings));
		add_result( $res, $test, FAIL, $msg );
	} else {
		add_result( $res, $test, PASS );
	}
	
	return @return_candidates;
}

sub show_results {
	my $url	= shift;
	my $res	= shift;
	my $opt	= shift;
	my $q	= shift;
	my @accept;
	push(@accept, { type => 'text/html', value => Accept('text/html') } );
	push(@accept, { type => 'application/json', value => Accept('application/json') } );
	push(@accept, { type => 'application/rdf+xml', value => Accept('application/rdf+xml') } );
	push(@accept, { type => 'text/turtle', value => Accept('text/turtle') } );
	push(@accept, { type => 'text/plain', value => Accept('text/plain') } );
	@accept	= sort { $b->{value} <=> $a->{value} || $b->{type} eq 'html' } @accept;
	my $a	= $accept[0];
	my $tested	= ($q->param('software')) ? iri($q->param('software')) : iri($url);
	if ($a->{type} eq 'text/html') {
		print $q->header( -type => 'text/html', -charset => 'utf-8');
		html_results($url, $tested, $res, $opt);
	} elsif ($a->{type} eq 'application/json') {
		my $data	= { endpoint => $url, results => $res };
		if (length($tested)) {
			$data->{software}	= $tested;
		}
		print $q->header( -type => $a->{type}, -charset => 'utf-8');
		print JSON->new->utf8->pretty->encode($data);
	} elsif ($a->{type} =~ m#^((application/rdf[+]xml)|(text/(turtle|plain)))$#) {
		print $q->header( -type => $a->{type}, -charset => 'utf-8');
		my $map		= RDF::Trine::NamespaceMap->new( { rdf => $rdf, earl => $earl, sdtest => $sdtest, dc => $dc } );
		my $type;
		if ($a->{type} =~ /turtle/) {
			$type	= 'turtle';
		} elsif ($a->{type} =~ /xml/) {
			$type	= 'rdfxml';
		} else {
			$type	= 'ntriples';
		}
		my $s		= RDF::Trine::Serializer->new( $type, namespaces => $map );
		rdf_results($url, $tested, $res, $s, $opt);
	} else {
		print $q->header( -type => 'text/plain', -charset => 'utf-8');
		print "should emit $a->{type}";
	}
}

sub results_model {
	my $url		= shift;
	my $tested	= shift;
	my $res		= shift;
	my $s		= shift;
	my $opt		= shift;
	my $model	= RDF::Trine::Model->new();
	my ($sec, $min, $hour, $day, $mon, $year)	= gmtime();
	$mon++;
	$year	+= 1900;
	my $time	= sprintf('%04d-%02d-%02dT%02d:%02d:%02dZ', $year, $mon, $day, $hour, $min, $sec);
	my $by		= iri($VALIDATOR_IRI);
	my @tests	= (REQUIRED_TESTS);
	if ($opt) {
		push(@tests, OPTIONAL_TESTS);
	}
	
	foreach my $test (@tests) {
		my $type	= test_type($test);
		my $desc	= DESCRIPTION->{ $test };
		no warnings 'uninitialized';
		my $status	= ($res->{$type}{$test}{result} eq PASS) ? $earl->pass : $earl->fail;
		
		my $a		= blank();
		my $r		= blank();
		$model->add_statement( statement($a, $rdf->type, $earl->Assertion) );
		$model->add_statement( statement($a, $earl->assertedBy, $by) );
		$model->add_statement( statement($a, $earl->subject, $tested) );
		$model->add_statement( statement($a, $earl->result, $r) );
		$model->add_statement( statement($a, $earl->test, $sdtest->$test()) );
		$model->add_statement( statement($r, $rdf->type, $earl->TestResult) );
		$model->add_statement( statement($r, $earl->outcome, $status) );
		$model->add_statement( statement($r, $dc->date, literal($time, undef, $xsd->dateTime)) );
		my @msg		= test_messages($res, $test);
		foreach my $m (@msg) {
			next unless (defined($m));
			my $st	= statement($r, $earl->info, literal($m));
			$model->add_statement( $st );
		}
	}
	return $model;
}

sub rdf_results {
	my $url		= shift;
	my $tested	= shift;
	my $res		= shift;
	my $s		= shift;
	my $opt		= shift;
	my $model	= results_model($url, $tested, $res, $s, $opt);
	$s->serialize_model_to_file( \*STDOUT, $model );
}

sub html_results {
	my $url	= shift;
	my $tested	= shift;
	my $res	= shift;
	my $opt		= shift;
	print_html_header();
	print_form($url, $tested);
	
	my $req_total	= 0;
	my $req_passed	= 0;
	my $req_failed	= 0;
	foreach my $test (REQUIRED_TESTS) {
		$req_total++;
		if (passed($res, $test)) {
			$req_passed++;
		} else {
			$req_failed++;
		}
	}
	
	my $opt_total	= 0;
	my $opt_passed	= 0;
	my $opt_failed	= 0;
	if ($opt) {
		foreach my $test (OPTIONAL_TESTS) {
			$opt_total++;
			if (passed($res, $test)) {
				$opt_passed++;
			} else {
				$opt_failed++;
			}
		}
	}
	
	my $total	= $req_total + $opt_total;
	my $passed	= $req_passed + $opt_passed;
	my $failed	= $req_failed + $opt_failed;
	
	my $req_class;
	if ($req_total == $req_passed) {
		$req_class	= 'pass';
	} elsif ($req_total == $req_failed) {
		$req_class	= 'fail';
	} else {
		$req_class	= 'fail';
	}
	
	my $opt_class;
	if ($opt) {
		if ($opt_total == $opt_passed) {
			$opt_class	= 'pass';
		} elsif ($opt_total == $opt_failed) {
			$opt_class	= 'fail';
		} else {
			$opt_class	= 'fail';
		}
	}
	
	if ($total == $passed) {
		print qq[<h1 id="summary" class="pass">All tests passed</h1>\n];
	} elsif ($req_total == $req_failed) {
		print qq[<h1 id="summary" class="fail">All required tests failed</h1>\n];
	} elsif ($req_total == $req_passed) {
		print qq[<h1 id="summary" class="warn">All required tests passed, but some tests failed</h1>\n];
	} else {
		print qq[<h1 id="summary" class="warn">Some tests failed</h1>\n];
	}
	
	print <<"END";
	<table>
		<tr>
			<th>Test</th>
			<th>Passed tests</th>
		</tr>
		<tr>
			<td><a href="#required">Required Tests</a></td>
			<td class="${req_class}">${req_passed}/${req_total}</td>
		</tr>
END
	if ($opt) {
		print <<"END";
		<tr>
			<td><a href="#optional">Best Practice Tests</a></td>
			<td class="${opt_class}">${opt_passed}/${opt_total}</td>
		</tr>
	</table>
END
	}
	
	print <<"END";
	<h2 id="required">Required Tests</h2>
	<ul>
END
	foreach my $test (REQUIRED_TESTS) {
		my $type	= test_type($test);
		my $desc	= DESCRIPTION->{ $test };
		no warnings 'uninitialized';
		my $status	= ($res->{$type}{$test}{result} eq PASS) ? qq[<abbr title="pass">✔ PASS</abbr>] : qq[<abbr title="fail">✘ FAIL</abbr>];
		my @msg		= test_messages($res, $test);
		my $msg		= scalar(@msg) ? join("<br/>", @msg) : '';
		my $class	= ($res->{$type}{$test}{result} eq PASS) ? 'pass' : 'fail';
		print <<"END";
		<li>
			<span class="${class}">${status}</span> ${desc}
END
		if (length($msg)) {
			print qq[\t\t\t<span class="details">$msg</span>\n];
		}
		
		print <<"END";
		</li>
END
	}
	print qq[\t</ul>\n];



	if ($opt) {
		print <<"END";
	<h2 id="required">Best Practice Tests</h2>
	<ul>
END
		foreach my $test (OPTIONAL_TESTS) {
			my $type	= test_type($test);
			my $desc	= DESCRIPTION->{ $test };
			no warnings 'uninitialized';
			my $status	= ($res->{$type}{$test}{result} eq PASS) ? qq[<abbr title="pass">✔ PASS</abbr>] : qq[<abbr title="fail">✘ FAIL</abbr>];
			my @msg		= test_messages($res, $test);
			my $msg		= scalar(@msg) ? join("<br/>", @msg) : '';
			my $class	= ($res->{$type}{$test}{result} eq PASS) ? 'pass' : 'fail';
			print <<"END";
		<li>
			<span class="${class}">${status}</span> ${desc}
END
			if (length($msg)) {
				print qq[\t\t\t<span class="details">$msg</span>\n];
			}
		
			print <<"END";
		</li>
END
		}
		print qq[\t</ul>\n];
	}
	
	print_html_footer();
}

sub print_form {
	my $url			= shift;
	my $software	= shift;
	print <<"END";
	<form action="" method="get">
		SPARQL Endpoint: <input name="url" id="url" type="text" size="40" value="$url" /><br/>
		Implementation software IRI: <input name="software" id="software" type="text" size="40" value="$software" /><br/>
		<input name="bp" id="bp" type="checkbox" value="1" /> Run best-practices tests<br/>
		<input name="submit" id="submit" type="submit" value="Submit" />
	</form>
END
}

sub print_html_header {
	print <<"END";
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8" />
	<title>SPARQL Service Description Report</title>
	<style type="text/css" title="text/css">
<!--
.fail {
	color: red;
}

#summary {
	text-align: center;
}

#summary.pass {
	color: white;
	background-color: green;
}

#summary.warn {
	color: white;
	background-color: orange;
}

#summary.fail {
	color: white;
	background-color: red;
}

.pass {
	color: green;
}

.details {
	display: block;
	width: 50%;
	border: 1px dashed #000;
	padding: 2px 1em;
	background-color: #ffa;
}

table {
	width: 100%;
	border-collapse: collapse;
}

th {
	border-bottom: 3px double #000;
}

td {
	border: 1px solid #999;
}

-->
</style>
</head>
<body>
END
}

sub print_html_footer {
	print <<"END";
</body>
</html>
END
}
