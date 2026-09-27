import groovy.json.JsonSlurper
import groovy.json.JsonOutput

def jsonSlurper = new JsonSlurper()
def secrets = jsonSlurper.parse(new File(args.size() > 1 ? args[1] : "secrets.json")).clients.inject([:]) { map, c -> map[c.client] = c.secret; map } 

def realm = jsonSlurper.parse(new File(args[0]))

for(client in realm.clients) {
  if(secrets[client.clientId]) {
    client.secret = secrets[client.clientId]
  }
}

def output = JsonOutput.toJson(realm)
def json = JsonOutput.prettyPrint(output)

println json
