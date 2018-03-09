import fake
TYPE = (
	"email",
	"name",
	"firstName",
	"lastName",
	"company",
	"user",
	"phone",
	"zip",
	"address",
	"city",
	"country",
	"day",
	"month",
	"seconds",
	"hour",
	"now",
	"number",
	"date",
	"word",
	"text",
	"title",
	"paragraph",
)
for t in TYPE:
	print ("{0:20s}: {1}".format(t, getattr(fake, t)()))
# EOF
